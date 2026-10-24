from sqlalchemy import func, select

from app.models import Ingredient, Recipe, RecipeIngredient
from app.seed.import_recipes import run_import
from app.seed.seed import load_json, run_seed, validate_ingredients, validate_recipes
from tests.conftest import DEMO_EMAIL


def _curated_names() -> set[str]:
    return {item["normalized_name"] for item in load_json("ingredients.json")["ingredients"]}


def _imported_names() -> set[str]:
    return {item["normalized_name"] for item in load_json("recipenlg_ingredients.json")["ingredients"]}


def test_shipped_import_data_is_valid():
    assert validate_ingredients(load_json("recipenlg_ingredients.json")) == []
    known = _curated_names() | _imported_names()
    assert validate_recipes(load_json("recipenlg_recipes.json"), known) == []


def test_imported_catalog_does_not_redefine_curated_ingredients():
    assert _curated_names() & _imported_names() == set()


def test_every_imported_ingredient_is_used_by_a_recipe():
    used = {
        line["ingredient"]
        for recipe in load_json("recipenlg_recipes.json")["recipes"]
        for line in recipe["ingredients"]
    }
    assert _imported_names() <= used


def test_reviewed_animal_products_list_the_matching_allergen():
    required = {"dairy": "milk", "egg": "egg", "fish": "fish", "shellfish": "shellfish"}
    for item in load_json("recipenlg_ingredients.json")["ingredients"]:
        allergen = required.get(item["animal_category"])
        if allergen and item["allergens_reviewed"]:
            assert allergen in item["allergens"], item["normalized_name"]


def test_imported_recipes_have_servings_instructions_and_ingredients():
    recipes = load_json("recipenlg_recipes.json")["recipes"]
    assert len(recipes) >= 1000
    for recipe in recipes:
        assert recipe["servings"] > 0
        assert len(recipe["instructions"]) >= 2
        assert len(recipe["ingredients"]) >= 3


def test_import_adds_recipes_without_touching_the_sample_set(db):
    run_seed(db, DEMO_EMAIL)
    sample_count = db.scalar(select(func.count()).select_from(Recipe))

    counts = run_import(db)

    assert counts["recipes"] == len(load_json("recipenlg_recipes.json")["recipes"])
    assert db.scalar(select(func.count()).select_from(Recipe)) == sample_count + counts["recipes"]
    # A curated ingredient keeps its hand-assigned label after the import.
    chicken = db.scalar(select(Ingredient).where(Ingredient.normalized_name == "chicken breast"))
    assert chicken.allergens_reviewed is True


def test_import_is_idempotent(db):
    run_seed(db, DEMO_EMAIL)
    run_import(db)
    recipes = db.scalar(select(func.count()).select_from(Recipe))
    lines = db.scalar(select(func.count()).select_from(RecipeIngredient))
    ingredients = db.scalar(select(func.count()).select_from(Ingredient))

    run_import(db)

    assert db.scalar(select(func.count()).select_from(Recipe)) == recipes
    assert db.scalar(select(func.count()).select_from(RecipeIngredient)) == lines
    assert db.scalar(select(func.count()).select_from(Ingredient)) == ingredients
