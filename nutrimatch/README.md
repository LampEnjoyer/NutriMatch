# NutriMatch

A better tomorrow starts with a better you.
NutriMatch is a platform for finding the best meals given your food and financial preferences.
Given your macronutrient and meal preferences, NutriMatch will suggest from a wide variety of meals. Estimated meal prices and nutrition facts are derived from the Kroger and USDA APIs respectively.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2 + Alembic + SQLite
- **Frontend:** React + React Router, TypeScript, Vite, Tailwind CSS 4

## Run it locally

Run the backend and frontend on separate terminals:

**Backend** (http://127.0.0.1:8000, API docs at `/docs`)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head               # creates nutrimatch.db
python -m app.seed.seed            # loads sample recipes and the demo user; safe to re-run
python -m app.seed.import_recipes  # (optional) load a larger recipe dataset (derived from recipeNLG)
uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173)

```bash
cd frontend
npm install
npm run dev
```

The data in `app/seed/data/recipenlg_*.json` is generated from the RecipeNLG-derived `corbt/all-recipes` dataset. See the module docstring in `tools/recipenlg/build.py` for the selection rules and `tools/recipenlg/labels.py` for how allergens are assigned.

## Verify

```bash
cd backend && python -m pytest          # 190 tests: seed, constraints, API, preferences, ranking, recipe import, units, pricing
cd frontend && npm run lint && npm run build
```

## Store prices (Kroger)

Prices come from the free [Kroger Public API](https://developer.kroger.com). Coverage is regional, so not every ZIP code has a store nearby.

1. Sign in at developer.kroger.com, create an application, and choose the `product.compact` scope.
2. Copy `backend/.env.example` to `backend/.env` and fill in `KROGER_CLIENT_ID` and `KROGER_CLIENT_SECRET`.
3. Restart the backend, open any recipe, enter a ZIP code in "Cost at the store", and pick a store.

How it works:

- Each ingredient is searched at the chosen store, using the search term and match rules in `app/seed/data/pricing.json`. For example, rules keep "butter" from matching peanut butter and "milk" from matching almond milk.
- Among matching products, the cheapest **per ounce, per fluid ounce or per item** wins, not the cheapest package. Sale prices count when they're lower.
- **This recipe** is the share of each package the recipe uses. **Shopping total** is the whole packages you'd buy. Pantry staples (salt, pepper) are shown but left out of both.
- Lookups are cached for `PRICE_CACHE_HOURS` (default 24) per ingredient and store. Every price shows its store and fetch time.
- A line that can't be priced has a few reasons: no matching product, no amount listed, nothing to buy, or a unit that can't be converted yet. For example: "3 tbsp butter" against butter sold by weight, or "2 cloves" against garlic sold by the bulb.

## Project layout

```
backend/
  app/               Core endpoints
  tools/recipenlg/   Regenerates imported recipe data (parse, label, select)
  alembic/           DB migrations
  nutrition/         USDA nutrition facts
  tests/
frontend/
  src/api/           API endpoints to backend/
  src/components/    Page components
  src/pages/         Core pages
  src/lib/           Utility functions
```

## Data Considerations

- **Recipes** include 22 sample recipes written for this prototype, not imported from a published source.
- **Imported recipes** (optional, see above) come from the RecipeNLG dataset, which scraped them from cooking sites. Their servings come from a "Serves N" line in the directions, meal type is guessed from the title, and cooking time, cuisine and images are not available.
- **Nutrition** facts have issues related to parsing. Not all ingredients have an associated USDA page, and not all sizes are able to be converted or identified, so nutrition facts might be incomplete.
- **Allergen tags** are also incomplete and do not encompass all ingredients, especially from the larger recipe set. Always verify allergen information!

## Next Steps

next steps here