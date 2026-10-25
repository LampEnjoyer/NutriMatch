import os, re, sys, json, sqlite3, httpx
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # so "app" can be imported from backend/
from app import units
from portions import FALLBACK_PORTIONS                             # nutrition/portions.py, next to this script

HERE = Path(__file__).resolve().parent          # backend/nutrition
BACKEND = HERE.parent                           # backend/, where .env and nutrimatch.db live

load_dotenv(dotenv_path=BACKEND / '.env')
api_key = os.getenv("USDA_KEY") or os.getenv("USDA_FDC_API_KEY")
if not api_key:
    raise SystemExit("USDA_KEY not found in backend/.env")

conn = sqlite3.connect(BACKEND / "nutrimatch.db")
BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# nutrient name in nutrition_facts -> USDA nutrient IDs to try, in order
NUTRIENT_IDS = {
    "calories":        [1008, 2047, 2048],
    "protein_g":       [1003],
    "carbohydrates_g": [1005],
    "fat_g":           [1004],
    "saturated_fat_g": [1258],
    "fiber_g":         [1079],
    "sugar_g":         [2000, 1063],
    "sodium_mg":       [1093],
}
CACHE = HERE / "fdc_nutrients_cache.json"          # saves API calls on re-runs
BATCH_SIZE = 20                                    # most foods POST /foods accepts per request
# Entry per fdc_id: {"nutrients": per-100 g values, "portions": gram weights}. Older entries held only
# nutrients; they lack the "nutrients" key and get fetched again.
cache = {k: v for k, v in (json.loads(CACHE.read_text()) if CACHE.exists() else {}).items() if "nutrients" in v}

# USDA portion labels -> millilitres, for working out density from e.g. "1 cup, chopped = 160 g".
VOLUME_ML = {
    "cup": units.MILLILITRES_PER_UNIT["cup"], "cups": units.MILLILITRES_PER_UNIT["cup"],
    "tbsp": units.MILLILITRES_PER_UNIT["tbsp"], "tablespoon": units.MILLILITRES_PER_UNIT["tbsp"],
    "tsp": units.MILLILITRES_PER_UNIT["tsp"], "teaspoon": units.MILLILITRES_PER_UNIT["tsp"],
    "fl oz": units.MILLILITRES_PER_UNIT["fl_oz"],
}
VOLUME_RE = re.compile(r"^(cups?|tbsp|tablespoon|tsp|teaspoon|fl oz)\b")
# Portions that are a weight or a package, not one whole item.
NOT_A_PIECE = re.compile(r"\b(oz|lb|serving|package|container|stick|pat|piece of|racc)\b")
# Which "one item" portion to prefer when USDA lists several sizes.
PIECE_PREFERENCE = ["medium", "large", "whole", "each", "small"]
PINCH_ML = units.MILLILITRES_PER_UNIT["tsp"] / 16


def parse_nutrients(food):
    """Per-100 g values for the NUTRIENT_IDS fields from one USDA food record. None = no data."""
    by_id = {}
    for n in food.get("foodNutrients", []):
        nutrient = n.get("nutrient") or {}
        if nutrient.get("id") is not None and n.get("amount") is not None:
            by_id[nutrient["id"]] = n["amount"]
    return {field: next((by_id[i] for i in ids if i in by_id), None) for field, ids in NUTRIENT_IDS.items()}


def parse_portions(food):
    """Gram weights from USDA's household portions: density (g/ml) and one piece, clove and slice."""
    density, clove, slice_, pieces = None, None, None, {}
    for p in food.get("foodPortions", []):
        grams, amount = p.get("gramWeight"), p.get("amount") or 1
        if not grams:
            continue
        unit_name = (p.get("measureUnit") or {}).get("name") or ""
        if unit_name in ("undetermined", "RACC"):   # RACC is a labelling serving size, not a household measure
            unit_name = ""
        text = " ".join(filter(None, [unit_name, p.get("modifier"), p.get("portionDescription")])).lower().strip()
        each = grams / amount
        volume = VOLUME_RE.match(text)
        if volume:
            density = density or each / VOLUME_ML[volume.group(1)]
        elif "clove" in text:
            clove = clove or each
        elif "slice" in text:
            if slice_ is None or "medium" in text:
                slice_ = each
        elif text and not NOT_A_PIECE.search(text):
            rank = next((i for i, word in enumerate(PIECE_PREFERENCE) if word in text), len(PIECE_PREFERENCE))
            pieces.setdefault(rank, each)
    piece = pieces[min(pieces)] if pieces else None
    return {"density": density, "piece": piece, "clove": clove, "slice": slice_}


def fetch_missing(fdc_ids):
    """Fills the cache for any of fdc_ids it doesn't have yet, 20 foods per request."""
    missing = sorted({str(i) for i in fdc_ids} - cache.keys())
    if not missing:
        return
    print(f"Fetching {len(missing)} foods from USDA")
    with httpx.Client(timeout=60) as client:
        for start in range(0, len(missing), BATCH_SIZE):
            batch = missing[start:start + BATCH_SIZE]
            r = client.post(f"{BASE_URL}/foods", params={"api_key": api_key},
                            json={"fdcIds": [int(i) for i in batch], "format": "full"})
            r.raise_for_status()
            for food in r.json():
                cache[str(food["fdcId"])] = {"nutrients": parse_nutrients(food), "portions": parse_portions(food)}
            for key in batch:                     # USDA leaves out IDs it can't find; don't ask again
                cache.setdefault(key, {"nutrients": {field: None for field in NUTRIENT_IDS},
                                       "portions": parse_portions({})})
            CACHE.write_text(json.dumps(cache))   # saved per batch, so an interrupted run keeps its progress


def to_grams(name, quantity, unit, density, per_count, portions):
    """Weight of one ingredient line. The ingredient's own data wins, then USDA's portions for the
    matched food, then the standard weights in portions.py."""
    fallback = FALLBACK_PORTIONS.get(name, {})
    density = density or portions["density"] or fallback.get("density")
    if unit == "pinch":
        return None if density is None else quantity * PINCH_ML * density
    if unit in ("clove", "slice"):
        each = portions[unit] or fallback.get(unit)
        return None if each is None else quantity * each
    return units.convert(quantity, unit, "g", density_g_per_ml=density,
                         grams_per_count=per_count or portions["piece"] or fallback.get("piece"))


recipes = conn.execute("SELECT id, title, servings FROM recipes ORDER BY id").fetchall()

# Every ingredient line of every recipe in one query, grouped by recipe.
lines_by_recipe = {}
for recipe_id, *line in conn.execute("""
    SELECT ri.recipe_id, i.normalized_name, i.fdc_id, i.density_g_per_ml, i.grams_per_count, ri.quantity, ri.unit
    FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
    ORDER BY ri.recipe_id, ri.position
"""):
    lines_by_recipe.setdefault(recipe_id, []).append(line)

fetch_missing(line[1] for lines in lines_by_recipe.values() for line in lines if line[1] is not None)

computed_at = datetime.now(timezone.utc).isoformat()
rows, with_exclusions = [], 0

for recipe_id, title, servings in recipes:
    totals = {field: 0.0 for field in NUTRIENT_IDS}
    excluded = []

    for name, fdc_id, density, per_count, quantity, unit in lines_by_recipe.get(recipe_id, []):
        if quantity is None or unit is None:
            excluded.append(f"{name} (no amount)"); continue
        if fdc_id is None:
            excluded.append(f"{name} (no USDA match)"); continue
        food = cache[str(fdc_id)]
        grams = to_grams(name, quantity, unit, density, per_count, food["portions"])
        if grams is None:
            excluded.append(f"{name} (can't convert {unit} to grams)"); continue

        for field, value in food["nutrients"].items():
            if value is not None:                 # missing nutrient counts as no data, not zero
                totals[field] += value * grams / 100

    per_serving = {k: round(v / servings, 1) for k, v in totals.items()}
    if excluded:
        with_exclusions += 1
    rows.append((recipe_id, per_serving["calories"], per_serving["protein_g"], per_serving["carbohydrates_g"],
                 per_serving["fat_g"], per_serving["saturated_fat_g"], per_serving["fiber_g"],
                 per_serving["sugar_g"], per_serving["sodium_mg"],
                 "USDA FoodData Central (Foundation, SR Legacy)", json.dumps(excluded), computed_at))

# Replace every per-serving row in one transaction.
conn.execute("DELETE FROM nutrition_facts WHERE serving_basis = 'per_serving'")
conn.executemany("""
    INSERT INTO nutrition_facts
      (recipe_id, serving_basis, calories, protein_g, carbohydrates_g, fat_g, saturated_fat_g,
       fiber_g, sugar_g, sodium_mg, data_source, is_estimated, excluded_ingredients, computed_at)
    VALUES (?, 'per_serving', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
""", rows)
conn.commit()
conn.close()

print(f"Saved nutrition for {len(rows)} recipes ({with_exclusions} leave out at least one ingredient)")
