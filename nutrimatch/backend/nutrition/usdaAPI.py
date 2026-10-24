import os, time, httpx, sqlite3, pandas as pd
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
api_key = os.getenv("USDA_KEY")
if not api_key:
    raise SystemExit("USDA_KEY not found in .env")

conn = sqlite3.connect("../nutrimatch.db")

df = pd.read_sql(
    "SELECT id, normalized_name, default_unit FROM ingredients WHERE fdc_id IS NULL ORDER BY normalized_name;",
    conn,
)

BASE_URL = "https://api.nal.usda.gov/fdc/v1"

BAD_WORDS = ["prepared", "frozen", "babyfood", "baby food", "restaurant", "fast food",
             "breaded", "roll", "sliced", "deli", "flavored", "sweetened", "mix",
             "infant", "imitation", "dehydrated", "substitute"]


def search_foods(query: str, page_size: int = 10) -> list[dict]:
    response = httpx.get(
        f"{BASE_URL}/foods/search",
        params={
            "api_key": api_key,
            "query": query,
            "dataType": "Foundation,SR Legacy",
            "pageSize": page_size,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("foods", [])


def pick_first_good(foods):
    for f in foods:
        d = f["description"].lower()
        if not any(w in d for w in BAD_WORDS):
            return f
    return foods[0] if foods else None


print(f"{len(df)} ingredients to match")

for row in df.itertuples():
    try:
        foods = search_foods(row.normalized_name)
    except httpx.HTTPError as exc:
        print(f"ERROR {row.normalized_name}: {exc}")
        continue

    picked = pick_first_good(foods)
    if picked is None:
        print(f"NONE  {row.normalized_name}")
        continue

    conn.execute("UPDATE ingredients SET fdc_id = ? WHERE id = ?", (picked["fdcId"], row.id))
    conn.commit()
    print(f"{row.normalized_name:<24} -> {picked['fdcId']} | {picked['description']}")
    time.sleep(0.2)

conn.close()    