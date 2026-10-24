"""Load the sample ingredient catalog, sample recipes and the demo user.

Run from backend/:  python -m app.seed.seed

Validation runs first and nothing is written if any check fails. Seeding is idempotent:
ingredients are matched on normalized_name and recipes on slug, so re-running updates
records in place instead of duplicating them.
"""

import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import vocab
from app.config import get_settings
from app.db import SessionLocal
from app.models import Ingredient, Recipe, RecipeIngredient, User, UserPreferences
from app.normalize import normalize_name

DATA_DIR = Path(__file__).parent / "data"


class SeedValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"{len(errors)} seed validation error(s)")


def load_json(filename: str) -> dict:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def _is_non_negative_int_or_none(value) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if not isinstance(value, int):
        return False
    return value >= 0


def validate_ingredients(data: dict) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(data.get("ingredients", [])):
        where = f"ingredients[{index}]"
        key = item.get("normalized_name")

        if not key:
            errors.append(f"{where}: missing normalized_name")
            continue
        where = f"ingredient '{key}'"

        if key != normalize_name(key):
            errors.append(f"{where}: normalized_name is not normalized (expected '{normalize_name(key)}')")
        if key in seen:
            errors.append(f"{where}: duplicate normalized_name")
        seen.add(key)

        if not item.get("name"):
            errors.append(f"{where}: missing name")

        default_unit = item.get("default_unit")
        if default_unit is not None and default_unit not in vocab.ALL_UNITS:
            errors.append(f"{where}: unknown default_unit '{default_unit}'")

        for allergen in item.get("allergens", []):
            if allergen not in vocab.ALLERGENS:
                errors.append(f"{where}: unknown allergen '{allergen}'")

        category = item.get("animal_category", "none")
        if category not in vocab.ANIMAL_CATEGORIES:
            errors.append(f"{where}: unknown animal_category '{category}'")

        if not isinstance(item.get("allergens_reviewed"), bool):
            errors.append(f"{where}: allergens_reviewed must be true or false")

    return errors


def validate_recipes(data: dict, known_ingredients: set[str]) -> list[str]:
    errors: list[str] = []
    seen_slugs: set[str] = set()

    for index, recipe in enumerate(data.get("recipes", [])):
        slug = recipe.get("slug")
        if not slug:
            errors.append(f"recipes[{index}]: missing slug")
            continue
        where = f"recipe '{slug}'"

        if slug in seen_slugs:
            errors.append(f"{where}: duplicate slug")
        seen_slugs.add(slug)

        if not recipe.get("title"):
            errors.append(f"{where}: missing title")

        meal_type = recipe.get("meal_type")
        if meal_type is not None and meal_type not in vocab.MEAL_TYPES:
            errors.append(f"{where}: unknown meal_type '{meal_type}'")

        servings = recipe.get("servings")
        if isinstance(servings, bool) or not isinstance(servings, int) or servings <= 0:
            errors.append(f"{where}: servings must be a positive integer")

        for field in ("preparation_time_min", "cooking_time_min", "inactive_time_min"):
            if not _is_non_negative_int_or_none(recipe.get(field)):
                errors.append(f"{where}: {field} must be a non-negative integer or null")

        instructions = recipe.get("instructions")
        if not isinstance(instructions, list) or len(instructions) == 0:
            errors.append(f"{where}: instructions must be a non-empty list")
        else:
            for step_index, step in enumerate(instructions):
                if not isinstance(step, str) or step.strip() == "":
                    errors.append(f"{where}: instructions[{step_index}] is empty")

        lines = recipe.get("ingredients")
        if not isinstance(lines, list) or len(lines) == 0:
            errors.append(f"{where}: ingredients must be a non-empty list")
            continue

        for line_index, line in enumerate(lines):
            line_where = f"{where} ingredients[{line_index}]"
            name = line.get("ingredient")
            if name not in known_ingredients:
                errors.append(f"{line_where}: ingredient '{name}' is not in the catalog")

            quantity = line.get("quantity")
            unit = line.get("unit")

            # Either both are present (a measured amount) or both are null ("to taste").
            if quantity is None and unit is not None:
                errors.append(f"{line_where}: unit '{unit}' given without a quantity")
            if quantity is not None and unit is None:
                errors.append(f"{line_where}: quantity given without a unit")

            if quantity is not None:
                if isinstance(quantity, bool) or not isinstance(quantity, (int, float)):
                    errors.append(f"{line_where}: quantity must be a number")
                elif quantity <= 0:
                    errors.append(f"{line_where}: quantity must be positive")

            if unit is not None and unit not in vocab.ALL_UNITS:
                errors.append(f"{line_where}: unknown unit '{unit}'")

    return errors


def _upsert_ingredients(session: Session, data: dict) -> dict[str, Ingredient]:
    existing = {}
    for ingredient in session.scalars(select(Ingredient)):
        existing[ingredient.normalized_name] = ingredient

    by_name: dict[str, Ingredient] = {}
    for item in data["ingredients"]:
        key = item["normalized_name"]
        ingredient = existing.get(key)
        if ingredient is None:
            ingredient = Ingredient(normalized_name=key)
            session.add(ingredient)

        ingredient.name = item["name"]
        ingredient.default_unit = item.get("default_unit")
        ingredient.allergens = list(item.get("allergens", []))
        ingredient.animal_category = item.get("animal_category", "none")
        ingredient.allergens_reviewed = item["allergens_reviewed"]
        # density_g_per_ml, grams_per_count and fdc_id are left untouched so Phase 3 data survives re-seeding.
        by_name[key] = ingredient

    session.flush()
    return by_name


def _upsert_recipes(session: Session, data: dict, ingredients: dict[str, Ingredient]) -> int:
    source_name = data.get("source_name", "NutriMatch sample recipe")

    existing = {}
    for recipe in session.scalars(select(Recipe)):
        existing[recipe.slug] = recipe

    count = 0
    for item in data["recipes"]:
        recipe = existing.get(item["slug"])
        if recipe is None:
            recipe = Recipe(slug=item["slug"])
            session.add(recipe)

        recipe.title = item["title"]
        recipe.description = item.get("description")
        recipe.cuisine = item.get("cuisine")
        recipe.meal_type = item.get("meal_type")
        recipe.preparation_time_min = item.get("preparation_time_min")
        recipe.cooking_time_min = item.get("cooking_time_min")
        recipe.inactive_time_min = item.get("inactive_time_min")
        recipe.servings = item["servings"]
        recipe.instructions = list(item["instructions"])
        recipe.image_url = item.get("image_url")
        recipe.source_name = item.get("source_name", source_name)
        recipe.source_url = item.get("source_url")
        recipe.ingredients_complete = True

        # Replace the ingredient lines wholesale; delete-orphan cascade removes the old rows.
        recipe.ingredients.clear()
        session.flush()
        for position, line in enumerate(item["ingredients"]):
            recipe.ingredients.append(
                RecipeIngredient(
                    ingredient=ingredients[line["ingredient"]],
                    position=position,
                    quantity=line.get("quantity"),
                    unit=line.get("unit"),
                    preparation_notes=line.get("notes"),
                    is_optional=line.get("optional", False),
                )
            )
        count += 1

    session.flush()
    return count


def _ensure_demo_user(session: Session, email: str) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name="Demo User", timezone="America/New_York")
        session.add(user)
        session.flush()
    if user.preferences is None:
        user.preferences = UserPreferences()
        session.flush()
    return user


def run_seed(session: Session, demo_email: str) -> dict[str, int]:
    ingredient_data = load_json("ingredients.json")
    recipe_data = load_json("recipes.json")

    errors = validate_ingredients(ingredient_data)
    known = set()
    for item in ingredient_data.get("ingredients", []):
        if item.get("normalized_name"):
            known.add(item["normalized_name"])
    errors.extend(validate_recipes(recipe_data, known))
    if len(errors) > 0:
        raise SeedValidationError(errors)

    ingredients = _upsert_ingredients(session, ingredient_data)
    recipe_count = _upsert_recipes(session, recipe_data, ingredients)
    _ensure_demo_user(session, demo_email)
    session.commit()

    return {"ingredients": len(ingredients), "recipes": recipe_count}


def main() -> int:
    session = SessionLocal()
    try:
        counts = run_seed(session, get_settings().demo_user_email)
    except SeedValidationError as exc:
        session.rollback()
        print("Seed data is invalid; nothing was written:", file=sys.stderr)
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    finally:
        session.close()

    print(f"Seeded {counts['ingredients']} ingredients and {counts['recipes']} recipes, plus the demo user.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
