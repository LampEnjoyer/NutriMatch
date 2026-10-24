# NutriMatch

Recipe discovery, nutrition tracking and grocery lists, ranked against your own goals.

**Status: Phase 1 (foundation).** The schema, migrations, sample data, a read-only recipe API and the app shell are in place. Search and ranking, nutrition calculation, meal logging and grocery lists are not built yet.

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

## Verify Phase 1

```bash
cd backend && python -m pytest          # 31 tests: seed validation, constraints, API
cd frontend && npm run build            # type-check and production build
```

Then open http://localhost:5173: the Discover page lists 22 recipes. Clicking one shows its ingredients, method and an empty nutrition panel.

## Project layout

```
backend/
  app/
    api/v1/          versioned routes (health, recipes)
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
