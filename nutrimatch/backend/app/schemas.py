from pydantic import BaseModel, ConfigDict


class RecipeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    description: str | None
    cuisine: str | None
    meal_type: str | None
    preparation_time_min: int | None
    cooking_time_min: int | None
    inactive_time_min: int | None
    total_time_min: int | None
    servings: int
    image_url: str | None


class RecipeIngredientOut(BaseModel):
    ingredient_id: int
    name: str
    normalized_name: str
    quantity: float | None
    unit: str | None
    preparation_notes: str | None
    is_optional: bool


class RecipeDetail(RecipeSummary):
    instructions: list[str]
    source_name: str
    source_url: str | None
    ingredients_complete: bool
    ingredients: list[RecipeIngredientOut]


class RecipeList(BaseModel):
    items: list[RecipeSummary]
    total: int


class ErrorResponse(BaseModel):
    detail: str
