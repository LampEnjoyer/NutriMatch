import copy

from sqlalchemy import func, select

from app.models import Ingredient, Recipe, RecipeIngredient, User
from app.seed.seed import load_json, run_seed, validate_ingredients, validate_recipes
from tests.conftest import DEMO_EMAIL


def _known_names() -> set[str]:
    names = set()
    for item in load_json("ingredients.json")["ingredients"]:
        names.add(item["normalized_name"])
    return names


def _one_recipe() -> dict:
    return copy.deepcopy(load_json("recipes.json")["recipes"][0])


def test_shipped_seed_data_is_valid():
    assert validate_ingredients(load_json("ingredients.json")) == []
    assert validate_recipes(load_json("recipes.json"), _known_names()) == []


def test_demo_scenario_has_at_least_three_alfredo_recipes_within_45_minutes():
    within_limit = []
    for recipe in load_json("recipes.json")["recipes"]:
        if "alfredo" not in recipe["title"].lower():
            continue
        total = recipe["preparation_time_min"] + recipe["cooking_time_min"]
        if total <= 45:
            within_limit.append(recipe["slug"])
    assert len(within_limit) >= 3


def test_rejects_unknown_unit():
    recipe = _one_recipe()
    recipe["ingredients"][0]["unit"] = "handful"
    errors = validate_recipes({"recipes": [recipe]}, _known_names())
    assert any("unknown unit 'handful'" in e for e in errors)


def test_rejects_quantity_without_unit_and_unit_without_quantity():
    recipe = _one_recipe()
    recipe["ingredients"][0]["unit"] = None
    recipe["ingredients"][1]["quantity"] = None
    errors = validate_recipes({"recipes": [recipe]}, _known_names())
    assert any("quantity given without a unit" in e for e in errors)
    assert any("given without a quantity" in e for e in errors)


def test_rejects_non_positive_and_non_numeric_quantities():
    recipe = _one_recipe()
    recipe["ingredients"][0]["quantity"] = 0
    recipe["ingredients"][1]["quantity"] = -2
    recipe["ingredients"][2]["quantity"] = "two"
    errors = validate_recipes({"recipes": [recipe]}, _known_names())
    assert sum("quantity must be positive" in e for e in errors) == 2
    assert any("quantity must be a number" in e for e in errors)


def test_accepts_to_taste_line():
    recipe = _one_recipe()
    recipe["ingredients"].append({"ingredient": "salt", "quantity": None, "unit": None})
    assert validate_recipes({"recipes": [recipe]}, _known_names()) == []


def test_rejects_unknown_ingredient_and_duplicate_slug():
    recipe = _one_recipe()
    recipe["ingredients"][0]["ingredient"] = "unicorn steak"
    errors = validate_recipes({"recipes": [recipe, copy.deepcopy(recipe)]}, _known_names())
    assert any("'unicorn steak' is not in the catalog" in e for e in errors)
    assert any("duplicate slug" in e for e in errors)


def test_rejects_bad_servings_meal_type_and_times():
    recipe = _one_recipe()
    recipe["servings"] = 0
    recipe["meal_type"] = "brunch"
    recipe["cooking_time_min"] = -5
    errors = validate_recipes({"recipes": [recipe]}, _known_names())
    assert any("servings must be a positive integer" in e for e in errors)
    assert any("unknown meal_type 'brunch'" in e for e in errors)
    assert any("cooking_time_min" in e for e in errors)


def test_rejects_bad_ingredient_catalog_entries():
    data = {
        "ingredients": [
            {"name": "Egg", "normalized_name": "Egg ", "allergens": ["egg"], "animal_category": "egg", "allergens_reviewed": True},
            {"name": "Nut", "normalized_name": "nut", "allergens": ["nuts"], "animal_category": "none", "allergens_reviewed": True},
            {"name": "Nut 2", "normalized_name": "nut", "allergens": [], "animal_category": "plant", "allergens_reviewed": "yes"},
        ]
    }
    errors = validate_ingredients(data)
    assert any("is not normalized" in e for e in errors)
    assert any("unknown allergen 'nuts'" in e for e in errors)
    assert any("duplicate normalized_name" in e for e in errors)
    assert any("unknown animal_category 'plant'" in e for e in errors)
    assert any("allergens_reviewed must be true or false" in e for e in errors)


def test_seed_is_idempotent(db):
    first = run_seed(db, DEMO_EMAIL)
    second = run_seed(db, DEMO_EMAIL)
    assert first == second

    assert db.scalar(select(func.count()).select_from(Recipe)) == first["recipes"]
    assert db.scalar(select(func.count()).select_from(Ingredient)) == first["ingredients"]
    assert db.scalar(select(func.count()).select_from(User)) == 1

    expected_lines = 0
    for recipe in load_json("recipes.json")["recipes"]:
        expected_lines += len(recipe["ingredients"])
    assert db.scalar(select(func.count()).select_from(RecipeIngredient)) == expected_lines


def test_seed_creates_demo_user_with_empty_preferences(seeded_db):
    user = seeded_db.scalar(select(User).where(User.email == DEMO_EMAIL))
    assert user is not None
    assert user.preferences is not None
    assert user.preferences.allergies == []
    assert user.preferences.nutrient_levels == {}
    assert user.preferences.meal_types == []
    assert user.preferences.time_preference is None
