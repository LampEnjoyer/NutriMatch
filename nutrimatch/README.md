# NutriMatch

Recipe discovery, nutrition tracking and grocery lists, ranked against your own goals.

**Status: Phase 1 (foundation) plus store pricing.** The schema, migrations, sample and imported recipes, a recipe API, the preferences form, preference-based ranking and store pricing (Kroger-family stores) are in place. Nutrition calculation, search, meal logging and grocery lists are not built yet.

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

**Larger recipe set (optional).** After the base seed, load about 1,500 imported recipes with instructions:

```bash
cd backend
python -m app.seed.import_recipes  # safe to re-run; never overwrites the hand-labelled sample ingredients
```

The data in `app/seed/data/recipenlg_*.json` is generated from the RecipeNLG-derived `corbt/all-recipes` dataset by `python -m tools.recipenlg.build path/to/shard.parquet` (needs `pip install -r requirements-tools.txt`). See the module docstring in `tools/recipenlg/build.py` for the selection rules and `tools/recipenlg/labels.py` for how allergens are assigned.

## Verify

```bash
cd backend && python -m pytest          # 190 tests: seed, constraints, API, preferences, ranking, recipe import, units, pricing
cd frontend && npm run lint && npm run build
```

Then open http://localhost:5173. The Discover page shows the preferences form beside the recipe list (22 sample recipes, or about 1,500 after the optional import). Choose preferences and press "Update recommendations": allergies hide recipes and everything else reorders them. Clicking a recipe shows its ingredients, method, an empty nutrition panel and the store-cost panel. Until nutrition is calculated, protein, fat and calorie preferences are reported as "not applied yet". Recipes with ingredients whose allergen data is unverified carry a "Check labels" note, and the recipe page lists those ingredients.

If you already have a local database, run `alembic upgrade head` first: the preferences table changed and the store tables were added.

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
    api/v1/          versioned routes (health, recipes, preferences, recommendations, pricing)
    pricing/         Kroger client, size parsing, product selection, recipe costing
    units.py         exact mass/volume conversions
    api/deps.py      DB session and current-user dependencies
    models.py        SQLAlchemy models
    ranking.py       recipe ranking (pure functions); recommend.py loads data for it
    schemas.py       Pydantic request and response models
    vocab.py         allowed units, allergens, diets, meal types
    seed/            seed and import scripts, JSON data
  tools/recipenlg/   regenerates the imported recipe data (parse, label, select)
  alembic/           migrations
  tests/
frontend/
  src/api/           typed API client
  src/components/    shell, status messages, nutrition label
  src/pages/         route pages
```

## Data: what's real and what isn't

- **Recipes** are 22 sample recipes written for this prototype, not imported from a published source. `source_name` says so, and `source_url` is null. They include five chicken Alfredo variants with different times for the demo scenario.
- **Imported recipes** (optional, see above) come from the RecipeNLG dataset, which scraped them from cooking sites; `source_name` says so. Their servings come from a "Serves N" line in the directions, meal type is guessed from the title, and cooking time, cuisine and images are not available. The dataset does not state a license, so check its terms before any public launch. Ingredient lines were parsed by rule: 327 of about 11,650 lines (unsized cans, unmeasured spices) have no quantity and are excluded from nutrition totals.
- **Nutrition** is not stored or shown yet. Phase 3 will compute it from ingredients using USDA FoodData Central and mark every value as estimated, with its source.
- **Allergen tags** were assigned by hand based on what each ingredient is. Packaged or blended products (broth, pasta, canned goods, spice blends, peanut butter, oats) are marked `allergens_reviewed: false` because their allergens vary by brand or carry cross-contact risk. Allergy filters must treat those as unknown, never as safe.
- **Conversion factors** (density, grams per piece) are empty until Phase 3 fills them from FoodData Central portion data. Nothing is guessed.

## Schema notes

The schema follows the spec, with these additions:

- `Ingredient.allergens`, `animal_category`, `allergens_reviewed`: allergies and diets act as hard filters, and gaps in allergen data stay visible.
- `Recipe.inactive_time_min`: overnight oats aren't reported as a 5-minute breakfast without a warning.
- `Recipe.ingredients_complete`: imports with unstructured ingredient lines can never be called allergy-safe.
- `UserPreferences` stores coarse levels instead of numeric targets: `nutrient_levels` (protein, fat, calories: low, high or don't care), `time_preference`, `meal_types`, `meal_size` (solo or family) and `allergies`. Only allergies are a hard filter; the rest will influence ranking. `GET /api/v1/preferences/options` describes the form questions as data, so adding a preference does not need a UI change.
- Recipe detail reports `unreviewed_ingredients` and `allergy_info_complete`, so the UI can tell users which ingredient labels to check themselves.
- `User.timezone`: daily totals use the user's calendar day.
- `MealLog.recipe_id` is `ON DELETE SET NULL` and the nutrition snapshot keeps the numbers, so deleting a recipe never rewrites meal history.

## Recommendations

`GET /api/v1/recommendations?limit=&offset=&q=` ranks every recipe for the current user's saved preferences. The algorithm is in `app/ranking.py` (pure functions, no database); `app/recommend.py` loads the data.

The optional `q` is the search box on the Discover page. It is live: the list updates as you type, after a short pause, with no button. (Preferences are different: they only apply when you press "Update recommendations".) Every word in it must appear in a recipe's title or description (ignoring case), so `salad` lists everything that says salad and `chicken salad` narrows it. Searching happens before allergy filtering and ranking, so preferences order the matches, and the "hidden by allergies" count only covers recipes that matched.

1. **Allergies filter.** A recipe is dropped if any ingredient lists one of the user's allergens. An ingredient with unreviewed allergen data is not assumed to contain allergens it does not list, so those recipes stay in and are flagged (`unreviewed_ingredients`) for the user to check.
2. **Everything else ranks.** Each preference the user set (not "don't care") scores a recipe from 0 to 1, and the recipe's score is the weighted average (`WEIGHTS`, equal for now).

There are no fixed thresholds. "High protein", "short" and "family" are judged by a recipe's percentile among the recipes still in the running: low and high pick the matching end, short and long the matching end of cooking time, medium the middle, solo and family the matching end of servings. A recipe with no value for a preference scores a neutral 0.5 on it and is marked `known: false`. If no recipe has data for a preference, for example before nutrition is computed, it is listed in `ignored_preferences` instead of silently doing nothing.

Per-serving nutrition is read from `nutrition_facts` rows with `serving_basis = 'per_serving'` (`calories`, `protein_g`, `fat_g`), so ranking by nutrition starts working as soon as those rows exist.

## Auth

None yet. Every request acts as the seeded demo user (`DEMO_USER_EMAIL`), resolved in `app/api/deps.py:get_current_user`. Real auth only needs to replace that function.
