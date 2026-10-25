"""Recipe read endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.models import Recipe, RecipeIngredient
from app.schemas import (
    ErrorResponse, NutritionOut, RecipeDetail, RecipeIngredientOut, RecipeList, RecipeSummary,
)


router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=RecipeList)
def list_recipes(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> RecipeList:
    total = db.scalar(select(func.count()).select_from(Recipe))
    recipes = db.scalars(select(Recipe).order_by(Recipe.title, Recipe.id).limit(limit).offset(offset)).all()

    items = []
    for recipe in recipes:
        items.append(RecipeSummary.model_validate(recipe))
    return RecipeList(items=items, total=total)


@router.get(
    "/{recipe_id}",
    response_model=RecipeDetail,
    responses={404: {"model": ErrorResponse}},
)
def get_recipe(recipe_id: int, db: DbSession) -> RecipeDetail:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.nutrition),
        )
    )
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recipe {recipe_id} not found")

    lines = []
    for line in recipe.ingredients:
        lines.append(
            RecipeIngredientOut(
                ingredient_id=line.ingredient_id,
                name=line.ingredient.name,
                normalized_name=line.ingredient.normalized_name,
                quantity=line.quantity,
                unit=line.unit,
                preparation_notes=line.preparation_notes,
                is_optional=line.is_optional,
                allergens=line.ingredient.allergens,
                animal_category=line.ingredient.animal_category,
                allergens_reviewed=line.ingredient.allergens_reviewed,
            )
        )

    # Each ingredient once, in recipe order, even if the recipe lists it on several lines.
    unreviewed = list(dict.fromkeys(line.name for line in lines if not line.allergens_reviewed))
    per_serving = None
    for row in recipe.nutrition:
        if row.serving_basis == "per_serving":
            per_serving = NutritionOut.model_validate(row)
    summary = RecipeSummary.model_validate(recipe)

    return RecipeDetail(
        **summary.model_dump(),
        instructions=recipe.instructions,
        source_name=recipe.source_name,
        source_url=recipe.source_url,
        ingredients_complete=recipe.ingredients_complete,
        ingredients=lines,
        unreviewed_ingredients=unreviewed,
        allergy_info_complete=recipe.ingredients_complete and len(unreviewed) == 0,
        nutrition=per_serving,
    )
