import os, re, sys, httpx, sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent   # backend/, where .env and nutrimatch.db live

load_dotenv(dotenv_path=BACKEND / '.env')
api_key = os.getenv("USDA_KEY") or os.getenv("USDA_FDC_API_KEY")
if not api_key:
    raise SystemExit("USDA_KEY not found in backend/.env")

BASE_URL = "https://api.nal.usda.gov/fdc/v1"
# USDA has no batch search, so run several searches at once. Keep this modest: the key allows
# about 1,000 requests an hour. By default only unmatched ingredients are searched; pass --all to
# redo every match (about 400 requests).
WORKERS = 8

# Words that point to a processed or different food. Each one only counts against a result when the
# ingredient name doesn't contain it, so "garlic powder" can still match a powder.
BAD_WORDS = {"prepared", "frozen", "babyfood", "baby", "restaurant", "fast", "breaded", "roll", "rolls",
             "sliced", "deli", "flavored", "sweetened", "mix", "infant", "imitation", "dehydrated",
             "substitute", "crackers", "cracker", "bread", "spread", "powder", "meatless", "canned",
             "cured", "concentrate", "juice", "industrial", "clarified", "ghee", "turbinado",
             "low-sodium", "reduced", "lowfat", "nonfat", "fat-free", "light", "diet", "cooked",
             "dried", "pickled", "free", "bun", "leave", "stick", "candied", "soup", "sauce", "salad", "pie", "cake", "cookies", "snacks"}
# Words that point to the plain, everyday form of a food.
GOOD_WORDS = {"raw", "whole", "granulated", "fluid", "plain", "regular", "distilled", "fresh", "table"}
# Category prefixes USDA puts before the food's real name, e.g. "Spices, cinnamon, ground".
CATEGORY_HEADS = {"spice", "leavening agent", "sugar", "nut"}
# Search phrases for staples the general scoring can't settle on its own (it would otherwise pick e.g.
# buttermilk for "milk" or wild rice for "rice"). The result must contain every word of the phrase.
QUERY_OVERRIDES = {
    "milk": "milk, whole, 3.25% milkfat",
    "vegetable oil": "oil, soybean, salad or cooking",
    "tomato": "tomatoes, red, ripe, raw",
    "lemon": "lemons, raw",
    "potato": "potatoes, flesh and skin, raw",
    "chicken": "chicken, broilers or fryers, meat only, raw",
    "rice": "rice, white, long-grain, regular, raw",
    "chicken broth": "soup, chicken broth, ready-to-serve",
    "beef broth": "soup, beef broth, ready-to-serve",
    "mushroom": "mushrooms, white, raw",
    "bacon": "pork, cured, bacon, unprepared",
    "water": "beverages, water, tap, drinking",
    # No "/" in phrases: USDA's search rejects it.
    "beef": "beef, ground, 80% lean meat, 20% fat, raw",
    "ground beef": "beef, ground, 80% lean meat, 20% fat, raw",
    "cinnamon": "spices, cinnamon, ground",
    "ketchup": "catsup",
    # Pasta shapes share one nutrition profile.
    "linguine": "pasta, dry, enriched",
    "fettuccine": "pasta, dry, enriched",
    "penne": "pasta, dry, enriched",
    "lasagna noodle": "pasta, dry, enriched",
    "shell macaroni": "pasta, dry, enriched",
    "egg noodle": "noodles, egg, dry, enriched",
    "cherry tomato": "tomatoes, red, ripe, raw",
    "red potato": "potatoes, red, flesh and skin, raw",
    "new potato": "potatoes, red, flesh and skin, raw",
    "unpeeled apple": "apples, raw, with skin",
    "chive": "chives, raw",
    "fresh ginger": "ginger root, raw",
    "ground cumin": "spices, cumin seed",
    "dry mustard": "spices, mustard seed, ground",
    "dijon mustard": "mustard, prepared, yellow",
    "red pepper flakes": "spices, pepper, red or cayenne",
    "smoked paprika": "spices, paprika",
    "salmon fillet": "fish, salmon, atlantic, farmed, raw",
    "snow pea": "peas, edible-podded, raw",
    "bean sprout": "mung beans, mature seeds, sprouted, raw",
    "dill pickle": "pickles, cucumber, dill or kosher dill",
    "processed cheese": "cheese, pasteurized process, american",
    "water chestnut": "waterchestnuts, chinese, canned",
    "crabmeat": "crustaceans, crab, blue, canned",
    "green grape": "grapes, red or green",
    "all-purpose flour": "wheat flour, white, all-purpose, enriched",
    "shortening": "shortening, vegetable, household, composite",
    "cream cheese": "cheese, cream",
    "sour cream": "cream, sour, cultured",
}

client = httpx.Client(timeout=30)


def search_foods(query: str, page_size: int = 25) -> list[dict]:
    response = client.get(
        f"{BASE_URL}/foods/search",
        params={
            "api_key": api_key,
            "query": query,
            "dataType": "Foundation,SR Legacy",
            "pageSize": page_size,
        },
    )
    response.raise_for_status()
    return response.json().get("foods", [])


def stem(word):
    """Crude singular: tomatoes -> tomato, onions -> onion, eggs -> egg."""
    for suffix in ("oes", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def words(text):
    return [stem(w) for w in re.findall(r"[a-z0-9%-]+", text.lower())]


def score(name, food):
    """Higher is a better match for the ingredient name, or None when the food is clearly not it."""
    wanted = words(name)
    description = food["description"].lower()
    found = words(description)
    # Every word of the ingredient must appear, and not as "no broth" / "without salt".
    if not all(w in found for w in wanted):
        return None
    if any(re.search(rf"\b(no|without)\s+{re.escape(w)}", description) for w in wanted):
        return None
    segments = description.split(",")
    head = words(segments[0])                       # "Onions" in "Onions, raw"
    if " ".join(head) in CATEGORY_HEADS and len(segments) > 1:
        head = words(segments[1])                   # "cinnamon" in "Spices, cinnamon, ground"
    points = 0.0
    if wanted[-1] in head:                          # the main noun names the food, not a side detail
        points += 3
    points -= sum(1 for w in head if w not in wanted)   # "Wild rice" and "Sweet potato leaves" are other foods
    if re.search(r"\b[A-Z]{3,}\b", food["description"]):   # branded products, e.g. "KRAFT ..."
        points -= 2
    points += sum(1 for w in found if w in GOOD_WORDS)
    points -= sum(3 for w in set(found) if w in BAD_WORDS and w not in wanted)
    points -= 0.2 * description.count(",")         # fewer qualifiers = more generic
    return points


def pick_best(name, foods):
    scored = [(s, i, f) for i, f in enumerate(foods) if (s := score(name, f)) is not None]
    if not scored:
        return None
    # Highest score; USDA's own ranking breaks ties.
    return max(scored, key=lambda t: (t[0], -t[1]))[2]


def match(row):
    """(ingredient id, name, picked food or None, error message or None). Runs in a worker thread."""
    ingredient_id, name = row
    query = QUERY_OVERRIDES.get(name, name)
    try:
        return ingredient_id, name, pick_best(query, search_foods(query)), None
    except httpx.HTTPStatusError as exc:   # str(exc) would print the URL, API key included
        return ingredient_id, name, None, f"HTTP {exc.response.status_code}"
    except httpx.HTTPError as exc:
        return ingredient_id, name, None, type(exc).__name__


conn = sqlite3.connect(BACKEND / "nutrimatch.db")
where = "" if "--all" in sys.argv else "WHERE fdc_id IS NULL"
rows = conn.execute(f"SELECT id, normalized_name FROM ingredients {where} ORDER BY normalized_name").fetchall()
print(f"{len(rows)} ingredients to match")

updates, no_match, errors = [], [], []
with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    for done, (ingredient_id, name, picked, error) in enumerate(pool.map(match, rows), start=1):
        if error:
            errors.append(f"{name}: {error}")
        elif picked is None:
            no_match.append(name)
        else:
            updates.append((picked["fdcId"], ingredient_id))
        if done % 50 == 0:
            print(f"  {done}/{len(rows)} searched")

# The database is only touched here, on the main thread, in one transaction.
conn.executemany("UPDATE ingredients SET fdc_id = ? WHERE id = ?", updates)
conn.commit()
conn.close()
client.close()

print(f"Matched {len(updates)}, no match {len(no_match)}, errors {len(errors)}")
if no_match:
    print("No USDA match: " + ", ".join(no_match))
for error in errors:
    print("ERROR " + error)
if errors:
    print("Run the script again to retry the errors.")
