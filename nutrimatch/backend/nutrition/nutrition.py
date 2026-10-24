import os, sys, json, time, sqlite3, httpx
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # so "app" can be imported from backend/
from app import units

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / '.env')
api_key = os.getenv("USDA_KEY")
if not api_key:
    raise SystemExit("USDA_KEY not found in .env")

conn = sqlite3.connect("../nutrimatch.db")
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
PER_ITEM_UNITS = {"clove", "slice", "pinch"}      # units.py leaves these out on purpose

CACHE = Path("fdc_nutrients_cache.json")           # saves API calls on re-runs
cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def nutrients_per_100g(fdc_id):
    key = str(fdc_id)
    if key in cache:
        return cache[key]
    r = httpx.get(f"{BASE_URL}/food/{fdc_id}", params={"api_key": api_key}, timeout=30)
    r.raise_for_status()
    by_id = {}
    for n in r.json().get("foodNutrients", []):
        nutrient = n.get("nutrient") or {}
        if nutrient.get("id") is not None and n.get("amount") is not None:
            by_id[nutrient["id"]] = n["amount"]
    result = {}
    for field, ids in NUTRIENT_IDS.items():
        result[field] = next((by_id[i] for i in ids if i in by_id), None)   # None = no data
    cache[key] = result
    CACHE.write_text(json.dumps(cache))
    time.sleep(0.2)
    return result


def to_grams(quantity, unit, density, per_count):
    if unit in PER_ITEM_UNITS:
        return None if per_count is None else quantity * per_count
    return units.convert(quantity, unit, "g", density_g_per_ml=density, grams_per_count=per_count)


recipes = conn.execute("SELECT id, title, servings FROM recipes ORDER BY id").fetchall()

for recipe_id, title, servings in recipes:
    lines = conn.execute("""
        SELECT i.normalized_name, i.fdc_id, i.density_g_per_ml, i.grams_per_count, ri.quantity, ri.unit
        FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ?
        ORDER BY ri.position
    """, (recipe_id,)).fetchall()

    totals = {field: 0.0 for field in NUTRIENT_IDS}
    excluded, total_grams = [], 0.0

    for name, fdc_id, density, per_count, quantity, unit in lines:
        if quantity is None or unit is None:
            excluded.append(f"{name} (no amount)"); continue
        if fdc_id is None:
            excluded.append(f"{name} (no USDA match)"); continue
        grams = to_grams(quantity, unit, density, per_count)
        if grams is None:
            excluded.append(f"{name} (can't convert {unit} to grams)"); continue

        per100 = nutrients_per_100g(fdc_id)
        total_grams += grams
        for field, value in per100.items():
            if value is not None:                 # missing nutrient counts as no data, not zero
                totals[field] += value * grams / 100

    per_serving = {k: round(v / servings, 1) for k, v in totals.items()}
    conn.execute("DELETE FROM nutrition_facts WHERE recipe_id = ? AND serving_basis = 'per_serving'", (recipe_id,))
    conn.execute("""
        INSERT INTO nutrition_facts
          (recipe_id, serving_basis, calories, protein_g, carbohydrates_g, fat_g, saturated_fat_g,
           fiber_g, sugar_g, sodium_mg, data_source, is_estimated, excluded_ingredients, computed_at)
        VALUES (?, 'per_serving', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    """, (recipe_id, per_serving["calories"], per_serving["protein_g"], per_serving["carbohydrates_g"],
          per_serving["fat_g"], per_serving["saturated_fat_g"], per_serving["fiber_g"],
          per_serving["sugar_g"], per_serving["sodium_mg"],
          "USDA FoodData Central (Foundation, SR Legacy)", json.dumps(excluded),
          datetime.now(timezone.utc).isoformat()))
    conn.commit()

    print(f"\n{title}  ({servings} servings, {total_grams / servings:.0f} g/serving, excluded: {len(excluded)})")
    print(f"  calories {per_serving['calories']} kcal | protein {per_serving['protein_g']} g | "
          f"carbs {per_serving['carbohydrates_g']} g | fat {per_serving['fat_g']} g")
    print(f"  sat fat {per_serving['saturated_fat_g']} g | fiber {per_serving['fiber_g']} g | "
          f"sugar {per_serving['sugar_g']} g | sodium {per_serving['sodium_mg']} mg")

conn.close()