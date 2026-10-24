# NutriMatch

Recipe discovery, nutrition tracking and grocery lists, ranked against your own goals.

**Status: Phase 1 (foundation) plus store pricing.** The schema, migrations, sample data, a read-only recipe API and the app shell are in place, and recipes can be priced at a Kroger-family store. Search and ranking, nutrition calculation, meal logging and grocery lists are not built yet.

## Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, SQLite (Postgres-compatible schema)
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS 4, React Router

## Run it locally

Two terminals, starting from the repo root.

**Backend** (http://127.0.0.1:8000, interactive API docs at `/docs`)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head               # creates nutrimatch.db
python -m app.seed.seed            # loads sample recipes and the demo user; safe to re-run
uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to the backend, so no CORS setup is needed in development.

## Verify

```bash
cd backend && python -m pytest          # 100 tests: seed, constraints, API, units, pricing
cd frontend && npm run lint && npm run build
```

Then open http://localhost:5173: the Discover page lists 22 recipes. Clicking one shows its ingredients, method, an empty nutrition panel and the store-cost panel.

## Store prices (Kroger)

Prices come from the [Kroger Public API](https://developer.kroger.com). It's free, and it covers Kroger-family stores (Kroger, Ralphs, Fred Meyer, King Soopers, Harris Teeter and others). Coverage is regional, so not every ZIP code has a store nearby.

1. Sign in at developer.kroger.com, create an application, and give it the `product.compact` scope.
2. Copy `backend/.env.example` to `backend/.env` and fill in `KROGER_CLIENT_ID` and `KROGER_CLIENT_SECRET`.
3. Restart the backend, open any recipe, enter a ZIP code in "Cost at the store", and pick a store.

How it works:

- Each ingredient is searched at the chosen store, using the search term and match rules in `app/seed/data/pricing.json`. Rules keep "butter" from matching peanut butter and "milk" from matching almond milk.
- Among matching products, the cheapest **per ounce, per fluid ounce or per item** wins, not the cheapest package. Sale prices count when they're lower.
- **This recipe** is the share of each package the recipe uses. **Shopping total** is the whole packages you'd buy. Pantry staples (salt, pepper) are shown but left out of both.
- Lookups are cached for `PRICE_CACHE_HOURS` (default 24) per ingredient and store. Every price shows its store and fetch time.
- A line that can't be priced says why: no matching product, no amount listed, nothing to buy, or a unit that can't be converted yet. Examples of the last: "3 tbsp butter" against butter sold by weight, or "2 cloves" against garlic sold by the bulb. Those conversions need the per-ingredient density and piece weights that Phase 3 loads from USDA FoodData Central. Until then, totals are marked incomplete.

Known gaps:

- Whether Kroger's product search returns a product page link wasn't confirmable from public docs. The client uses `productPageURI` if present and otherwise links to a Kroger search for the product.
- The meaning of `soldBy: WEIGHT` prices hasn't been checked against live data. Those lines are flagged "sold by weight".
- There is no way yet to swap the chosen product for a different one. `IngredientProductMatch.selected_by = "user"` is in the schema for that.

## Project layout

```
backend/
  app/
    api/v1/          versioned routes (health, recipes, pricing)
    pricing/         Kroger client, size parsing, product selection, recipe costing
    units.py         exact mass/volume conversions
    api/deps.py      DB session and current-user dependencies
    models.py        SQLAlchemy models
    schemas.py       Pydantic response models
    vocab.py         allowed units, allergens, diets, meal types
    seed/            seed script and JSON data
  alembic/           migrations
  tests/
frontend/
  src/api/           typed API client
  src/components/    shell, status messages, nutrition label
  src/pages/         route pages
```

## Data: what's real and what isn't

- **Recipes** are 22 sample recipes written for this prototype, not imported from a published source. `source_name` says so, and `source_url` is null. They include five chicken Alfredo variants with different times for the demo scenario.
- **Nutrition** is not stored or shown yet. Phase 3 will compute it from ingredients using USDA FoodData Central and mark every value as estimated, with its source.
- **Allergen tags** were assigned by hand based on what each ingredient is. Packaged or blended products (broth, pasta, canned goods, spice blends, peanut butter, oats) are marked `allergens_reviewed: false` because their allergens vary by brand or carry cross-contact risk. Allergy filters must treat those as unknown, never as safe.
- **Conversion factors** (density, grams per piece) are empty until Phase 3 fills them from FoodData Central portion data. Nothing is guessed.

## Schema notes

The schema follows the spec, with these additions:

- `Ingredient.allergens`, `animal_category`, `allergens_reviewed`: allergies and diets act as hard filters, and gaps in allergen data stay visible.
- `Recipe.inactive_time_min`: overnight oats aren't reported as a 5-minute breakfast without a warning.
- `Recipe.ingredients_complete`: imports with unstructured ingredient lines can never be called allergy-safe.
- `UserPreferences` hard-limit flags per field, plus optional ranking weights.
- `User.timezone`: daily totals use the user's calendar day.
- `MealLog.recipe_id` is `ON DELETE SET NULL` and the nutrition snapshot keeps the numbers, so deleting a recipe never rewrites meal history.

## Auth

None yet. Every request acts as the seeded demo user (`DEMO_USER_EMAIL`), resolved in `app/api/deps.py:get_current_user`. Real auth only needs to replace that function.
