from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Ingredient, MealLog, Recipe, RecipeIngredient, SavedRecipe, User


def _recipe(**overrides) -> Recipe:
    values = {"slug": "test", "title": "Test", "servings": 2, "instructions": ["Cook."], "source_name": "test"}
    values.update(overrides)
    return Recipe(**values)


def test_total_time_adds_prep_and_cook_but_not_inactive():
    assert _recipe(preparation_time_min=10, cooking_time_min=25, inactive_time_min=360).total_time_min == 35
    assert _recipe(preparation_time_min=5, cooking_time_min=None).total_time_min == 5
    assert _recipe(preparation_time_min=None, cooking_time_min=None).total_time_min is None


def test_deleting_a_recipe_keeps_meal_history(seeded_db):
    db = seeded_db
    user = db.scalar(select(User))
    recipe = db.scalar(select(Recipe).where(Recipe.slug == "spinach-feta-scrambled-eggs"))
    log = MealLog(
        user_id=user.id,
        recipe_id=recipe.id,
        meal_slot="breakfast",
        consumed_at=datetime(2026, 10, 24, 12, 0, tzinfo=UTC),
        servings_consumed=1,
        nutrition_snapshot={"title": recipe.title, "calories": None},
    )
    db.add(log)
    db.commit()

    db.delete(recipe)
    db.commit()
    db.expire_all()

    kept = db.get(MealLog, log.id)
    assert kept is not None
    assert kept.recipe_id is None
    assert kept.nutrition_snapshot["title"] == "Spinach and Feta Scrambled Eggs"


def test_ingredient_in_use_cannot_be_deleted(seeded_db):
    db = seeded_db
    egg = db.scalar(select(Ingredient).where(Ingredient.normalized_name == "egg"))
    db.delete(egg)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_recipe_rejects_non_positive_servings(db):
    db.add(_recipe(servings=0))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_recipe_ingredient_rejects_non_positive_quantity(seeded_db):
    db = seeded_db
    recipe = db.scalar(select(Recipe))
    salt = db.scalar(select(Ingredient).where(Ingredient.normalized_name == "salt"))
    db.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=salt.id, quantity=-1, unit="tsp"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_a_recipe_can_only_be_saved_once_per_user(seeded_db):
    db = seeded_db
    user = db.scalar(select(User))
    recipe = db.scalar(select(Recipe))
    db.add(SavedRecipe(user_id=user.id, recipe_id=recipe.id))
    db.commit()
    db.add(SavedRecipe(user_id=user.id, recipe_id=recipe.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
