"""Loads recipes from the database, ranks them for a user and builds the response."""

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.orm import Session, defer

from app.models import Ingredient, NutritionFacts, Recipe, RecipeIngredient, UserPreferences
from app.ranking import IngredientInfo, RankingPreferences, RecipeFeatures, rank_recipes
from app.schemas import RecipeSummary, RecommendationItem, RecommendationList, ScoreComponent

NUTRITION_COLUMNS = {
    "protein": NutritionFacts.protein_g,
    "fat": NutritionFacts.fat_g,
    "calories": NutritionFacts.calories,
}


def to_ranking_preferences(preferences: UserPreferences | None) -> RankingPreferences:
    if preferences is None:
        return RankingPreferences()
    return RankingPreferences(
        nutrient_levels=dict(preferences.nutrient_levels or {}),
        time_preference=preferences.time_preference,
        meal_types=tuple(preferences.meal_types or ()),
        meal_size=preferences.meal_size,
        allergies=frozenset(preferences.allergies or ()),
    )


def _like_pattern(word: str) -> str:
    """A contains-pattern for `word` in which %, _ and \\ match themselves."""
    escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search_conditions(query: str | None) -> list[ColumnElement[bool]]:
    """One condition per word: it must appear in the title or description, ignoring case."""
    conditions = []
    for word in (query or "").split():
        pattern = _like_pattern(word)
        conditions.append(or_(Recipe.title.ilike(pattern, escape="\\"), Recipe.description.ilike(pattern, escape="\\")))
    return conditions


def load_features(db: Session, query: str | None = None) -> list[RecipeFeatures]:
    # Instructions are the bulk of a recipe row and ranking never needs them.
    statement = select(Recipe).options(defer(Recipe.instructions))
    for condition in search_conditions(query):
        statement = statement.where(condition)
    recipes = db.scalars(statement).all()

    ingredients: dict[int, list[IngredientInfo]] = {}
    lines = db.execute(
        select(RecipeIngredient.recipe_id, Ingredient.name, Ingredient.allergens, Ingredient.allergens_reviewed)
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .order_by(RecipeIngredient.recipe_id, RecipeIngredient.position)
    )
    for recipe_id, name, allergens, reviewed in lines:
        ingredients.setdefault(recipe_id, []).append(IngredientInfo(name, frozenset(allergens or ()), reviewed))

    nutrients: dict[int, dict[str, float | None]] = {}
    rows = db.execute(
        select(NutritionFacts.recipe_id, *NUTRITION_COLUMNS.values()).where(NutritionFacts.serving_basis == "per_serving")
    )
    for recipe_id, *values in rows:
        nutrients[recipe_id] = dict(zip(NUTRITION_COLUMNS, values))

    return [
        RecipeFeatures(
            id=recipe.id,
            title=recipe.title,
            meal_type=recipe.meal_type,
            total_time_min=recipe.total_time_min,
            servings=recipe.servings,
            nutrients=nutrients.get(recipe.id, {}),
            ingredients=ingredients.get(recipe.id, []),
            ingredients_complete=recipe.ingredients_complete,
        )
        for recipe in recipes
    ]


def recommend(
    db: Session, preferences: UserPreferences | None, limit: int, offset: int, query: str | None = None
) -> RecommendationList:
    # Searching narrows the pool first, so ranking compares recipes among the matches.
    result = rank_recipes(load_features(db, query), to_ranking_preferences(preferences))
    page = result.ranked[offset : offset + limit]

    recipes = {r.id: r for r in db.scalars(select(Recipe).where(Recipe.id.in_([p.recipe.id for p in page])))}
    items = []
    for ranked in page:
        items.append(
            RecommendationItem(
                **RecipeSummary.model_validate(recipes[ranked.recipe.id]).model_dump(),
                score=ranked.score,
                components=[ScoreComponent(key=c.key, score=c.score, known=c.known) for c in ranked.components],
                unreviewed_ingredients=list(ranked.unreviewed_ingredients),
                allergy_info_complete=ranked.allergy_info_complete,
            )
        )
    return RecommendationList(
        items=items,
        total=len(result.ranked),
        excluded_for_allergies=result.excluded_for_allergies,
        ranked_by=result.ranked_by,
        ignored_preferences=result.ignored,
    )
