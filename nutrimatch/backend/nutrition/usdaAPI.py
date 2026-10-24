import os, httpx, sqlite3, pandas as pd
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / '.env'

conn = sqlite3.connect("../nutrimatch.db")

df = pd.read_sql("SELECT id, normalized_name, default_unit FROM ingredients WHERE fdc_id IS NULL ORDER BY normalized_name;", conn)

load_dotenv(dotenv_path=env_path)

api_key = os.getenv("USDA_KEY")

BASE_URL = "https://api.nal.usda.gov/fdc/v1"

def search_foods(query: str, page_size: int = 10) -> list[dict]:
    response = httpx.get(
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

for row in df.itertuples():
    query = row.normalized_name
    while True:
        foods = search_foods(query)
        print(f"\n=== {row.normalized_name} (searching: '{query}') ===")
        for i, food in enumerate(foods, 1):
            print(f"{i:>2}. {food['fdcId']} | {food['dataType']} | {food['description']}")

        choice = input("number to save, s = skip, q = quit, or type a new search: ").strip()

        if choice.lower() == "q":
            conn.close()
            raise SystemExit
        if choice.lower() == "s":
            break
        if choice.isdigit() and 1 <= int(choice) <= len(foods):
            fdc_id = foods[int(choice) - 1]["fdcId"]
            conn.execute("UPDATE ingredients SET fdc_id = ? WHERE id = ?", (fdc_id, row.id))
            conn.commit()
            print(f"saved {fdc_id}")
            break
        query = choice   # anything else is treated as a new search term

conn.close()