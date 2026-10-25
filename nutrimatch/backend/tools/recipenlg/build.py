"""Build the imported seed files from a RecipeNLG-style parquet shard (corbt/all-recipes).

Run from backend/ (needs pyarrow, see requirements-tools.txt):

    python -m tools.recipenlg.build path/to/shard.parquet

Writes app/seed/data/recipenlg_recipes.json and recipenlg_ingredients.json. Selection is
deterministic for a given shard and --seed. Recipes are kept only when they:
  - state their servings,
  - have ingredient lines that parse to a name and a convertible amount,
  - use only the most common ingredient names, so every ingredient can be labelled for allergens.
"""

import argparse
import collections
import hashlib
import json
import random
import re
from pathlib import Path

from tools.recipenlg.labels import label_for
from tools.recipenlg.parse import parse_ingredient, parse_recipe

SEED_DIR = Path(__file__).resolve().parents[2] / "app" / "seed" / "data"
SOURCE_NAME = "RecipeNLG (corbt/all-recipes)"

# Unmeasured lines are tolerated only for things that are normally added to taste.
UNMEASURED_OK = {"salt", "black pepper", "water", "vegetable oil", "olive oil", "all-purpose flour", "sugar", "butter",
                 "cinnamon", "nutmeg", "parsley", "paprika"}
# Fragments left over from parsing; a recipe containing one is dropped.
REJECT_NAMES = {"", "1", "1 1", "'n", "short", "brown", "shelled", "toast", "crumb", "sauce", "round", "cut", "red", "green",
                "yellow", "hot", "nut", "meat", "bean", "fruit", "syrup", "broth", "cereal", "chili", "curry", "squash",
                "cake", "mashed", "cubed", "drained"}

BAKING = re.compile(
    r"\b(cake|cookie|cookies|pie|candy|fudge|brownie|brownies|muffin|muffins|bread|cobbler|frosting|icing|pudding|bars?|"
    r"dessert|cupcakes?|pastry|tart|truffle|toffee|brittle|punch|jello|jell-o|roll|rolls|biscuits?|cheesecake|crisp|donut|"
    r"doughnut|scone|pancake|waffle|crepe|ice cream|sundae|parfait|mousse|cream puff|chocolate|caramel|marshmallow)\b", re.I)

MEAL_RULES = [
    ("breakfast", re.compile(r"\b(breakfast|pancake|waffle|omelet|omelette|french toast|granola|oatmeal|muffin|scramble|frittata|quiche|hash brown|crepe)", re.I)),
    ("snack", re.compile(r"\b(dip|snack|trail mix|popcorn|appetizer|bites?|spread|cookie|cookies|bar|bars|candy|fudge|brownie|brownies|cake|pie|pudding|dessert|punch|cupcakes?|chocolate|caramel|marshmallow|frosting|icing|toffee|brittle|truffle)\b", re.I)),
    ("lunch", re.compile(r"\b(sandwich|salad|wrap|soup|sub|burger|burrito|taco)", re.I)),
]

PROTEIN_CLASSES = [
    ("poultry", ("chicken", "turkey", "duck")),
    ("beef", ("beef", "steak", "veal", "roast")),
    ("pork", ("pork", "ham", "bacon", "sausage")),
    ("seafood", ("shrimp", "tuna", "salmon", "fish", "crab", "cod", "scallop", "lobster", "clam", "tilapia", "trout")),
    ("legume", ("bean", "lentil", "chickpea", "tofu", "pea ", "peanut butter")),
]
# Share of the final set per main-ingredient class, so the set is not mostly baking.
QUOTA = {"poultry": 0.18, "beef": 0.14, "pork": 0.10, "seafood": 0.10, "legume": 0.08, "egg_dairy": 0.08,
         "plant_other": 0.17, "baking": 0.15}


def meal_type(title: str) -> str:
    for label, pattern in MEAL_RULES:
        if pattern.search(title):
            return label
    return "dinner"


def classify(names: set[str], title: str) -> str:
    if BAKING.search(title):
        return "baking"
    joined = " | ".join(names) + " | " + title.lower()
    for label, keys in PROTEIN_CLASSES:
        if any(key in joined for key in keys):
            return label
    return "egg_dairy" if ("egg" in names or any("cheese" in n for n in names)) else "plant_other"


def parse_candidates(texts: list[str]) -> tuple[list[dict], collections.Counter]:
    rejected: collections.Counter = collections.Counter()
    parsed = []
    for text in texts:
        recipe = parse_recipe(text)
        if not recipe:
            rejected["unparseable"] += 1
            continue
        if not (3 <= len(recipe["ingredient_lines"]) <= 16 and 2 <= len(recipe["steps"]) <= 14):
            rejected["size_out_of_range"] += 1
            continue
        if recipe["servings"] is None or not (1 <= recipe["servings"] <= 24):
            rejected["no_servings"] += 1
            continue
        if not re.fullmatch(r"[A-Za-z0-9 ,'&()!.\-éèñ]{4,80}", recipe["title"]):
            rejected["odd_title"] += 1
            continue
        lines = [parse_ingredient(line) for line in recipe["ingredient_lines"]]
        if any(not l["name"] or len(l["name"].split()) > 4 or len(l["name"]) > 40 for l in lines):
            rejected["bad_name"] += 1
            continue
        if not all(l["measured"] or l["name"] in UNMEASURED_OK for l in lines):
            rejected["unmeasured_non_staple"] += 1
            continue
        if sum(l["convertible"] for l in lines) / len(lines) < 0.8:
            rejected["too_many_unconvertible"] += 1
            continue
        recipe["lines"] = lines
        parsed.append(recipe)
    return parsed, rejected


def dedupe_by_title(recipes: list[dict]) -> list[dict]:
    seen, unique = set(), []
    for recipe in recipes:
        key = re.sub(r"[^a-z]", "", recipe["title"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(recipe)
    return unique


def select(recipes: list[dict], target: int, vocab_size: int, rng: random.Random) -> list[dict]:
    frequency = collections.Counter(n for r in recipes for n in {l["name"] for l in r["lines"]})
    vocab = {name for name, _ in frequency.most_common(vocab_size)}
    covered = [r for r in recipes if all(l["name"] in vocab and l["name"] not in REJECT_NAMES for l in r["lines"])]
    for recipe in covered:
        recipe["protein"] = classify({l["name"] for l in recipe["lines"]}, recipe["title"])

    rng.shuffle(covered)
    picked, per_class = [], collections.Counter()
    for recipe in covered:
        if per_class[recipe["protein"]] >= QUOTA[recipe["protein"]] * target:
            continue
        per_class[recipe["protein"]] += 1
        picked.append(recipe)
        if len(picked) >= target:
            break
    print(f"{len(covered)} recipes fit the {vocab_size}-name vocabulary; picked {len(picked)}: {dict(per_class)}")
    return picked


def tidy_title(title: str) -> str:
    # The source title-cases every word, giving "Jane'S Chili".
    return re.sub(r"(?<=[A-Za-z0-9.])'S\b", "'s", title)


def recipe_entry(recipe: dict) -> dict:
    title = tidy_title(recipe["title"])
    slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:90]
    ingredients = []
    for line in recipe["lines"]:
        # A container with no stated size has no usable amount: store it as unmeasured.
        measured = line["unit"] is not None
        ingredients.append({
            "ingredient": line["name"],
            "quantity": line["quantity"] if measured else None,
            "unit": line["unit"] if measured else None,
            "notes": (line["notes"] or None) and line["notes"][:200],
        })
    return {
        "slug": f"{slug_base}-{hashlib.sha1(recipe['title'].encode()).hexdigest()[:6]}",
        "title": title,
        "meal_type": meal_type(recipe["title"]),
        "servings": recipe["servings"],
        "ingredients": ingredients,
        "instructions": recipe["steps"],
    }


def ingredient_entries(recipes: list[dict]) -> tuple[list[dict], list[str]]:
    units: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for entry in recipes:
        for line in entry["ingredients"]:
            if line["unit"]:
                units[line["ingredient"]][line["unit"]] += 1
    entries, unlabelled = [], []
    for name in sorted({line["ingredient"] for entry in recipes for line in entry["ingredients"]}):
        label = label_for(name)
        if label is None:
            unlabelled.append(name)
        common = units[name].most_common(1)
        entries.append({
            "name": name[0].upper() + name[1:],
            "normalized_name": name,
            "default_unit": common[0][0] if common else None,
            "allergens": list(label.allergens) if label else [],
            "animal_category": label.animal_category if label else "none",
            "allergens_reviewed": label.reviewed if label else False,
        })
    return entries, unlabelled


def main() -> None:
    import pyarrow.parquet as pq

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("parquet", type=Path)
    parser.add_argument("--out", type=Path, default=SEED_DIR)
    parser.add_argument("--target", type=int, default=1500, help="number of recipes to select")
    parser.add_argument("--vocab-size", type=int, default=400, help="most common ingredient names recipes may use")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    texts = pq.read_table(args.parquet).column("input").to_pylist()
    parsed, rejected = parse_candidates(texts)
    unique = dedupe_by_title(parsed)
    print(f"{len(texts)} recipes read, {len(parsed)} parsed cleanly, {len(unique)} after title de-duplication")
    print("rejected:", dict(rejected))

    picked = select(unique, args.target, args.vocab_size, random.Random(args.seed))
    recipes = [recipe_entry(r) for r in sorted(picked, key=lambda r: r["title"])]
    ingredients, unlabelled = ingredient_entries(recipes)

    curated = {i["normalized_name"] for i in json.loads((SEED_DIR / "ingredients.json").read_text(encoding="utf-8"))["ingredients"]}
    new_ingredients = [i for i in ingredients if i["normalized_name"] not in curated]
    reviewed = sum(i["allergens_reviewed"] for i in ingredients)
    print(f"{len(ingredients)} ingredients used ({len(ingredients) - len(new_ingredients)} already in the curated catalog), "
          f"{reviewed} with reviewed allergens, {len(unlabelled)} unlabelled")
    if unlabelled:
        print("unlabelled (add to labels.py):", ", ".join(unlabelled))

    args.out.mkdir(parents=True, exist_ok=True)
    note = ("Generated by tools/recipenlg/build.py from the RecipeNLG-derived corbt/all-recipes dataset. "
            "A null quantity means 'to taste' or an unsized container and is excluded from nutrition totals.")
    (args.out / "recipenlg_recipes.json").write_text(
        json.dumps({"_note": note, "source_name": SOURCE_NAME, "recipes": recipes}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "recipenlg_ingredients.json").write_text(
        json.dumps({"_note": note, "ingredients": new_ingredients}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(recipes)} recipes and {len(new_ingredients)} new ingredients to {args.out}")


if __name__ == "__main__":
    main()
