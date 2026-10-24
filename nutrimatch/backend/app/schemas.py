from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import vocab


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
    allergens: list[str]
    animal_category: str
    # False means the allergens above are not known to be complete (blended or branded products).
    allergens_reviewed: bool


class RecipeDetail(RecipeSummary):
    instructions: list[str]
    source_name: str
    source_url: str | None
    ingredients_complete: bool
    ingredients: list[RecipeIngredientOut]
    # Names of ingredients whose allergen data is unverified. The user should check those labels.
    unreviewed_ingredients: list[str]
    # True only when every ingredient is structured and has reviewed allergen data.
    allergy_info_complete: bool


class RecipeList(BaseModel):
    items: list[RecipeSummary]
    total: int


class ErrorResponse(BaseModel):
    detail: str


def _unique_members(values: list[str], allowed: frozenset[str], what: str) -> list[str]:
    for value in values:
        if value not in allowed:
            raise ValueError(f"unknown {what} '{value}'; allowed: {', '.join(sorted(allowed))}")
    return list(dict.fromkeys(values))


class PreferencesIn(BaseModel):
    """A full replacement of the user's preferences. Omitted fields mean "no preference"."""

    model_config = ConfigDict(extra="forbid")

    nutrient_levels: dict[str, str] = {}
    time_preference: str | None = None
    meal_types: list[str] = []
    meal_size: str | None = None
    allergies: list[str] = []

    @field_validator("nutrient_levels")
    @classmethod
    def _check_nutrient_levels(cls, value: dict[str, str]) -> dict[str, str]:
        for nutrient, level in value.items():
            if nutrient not in vocab.NUTRIENT_KEYS:
                raise ValueError(f"unknown nutrient '{nutrient}'; allowed: {', '.join(sorted(vocab.NUTRIENT_KEYS))}")
            if level not in vocab.LEVELS:
                raise ValueError(f"unknown level '{level}' for {nutrient}; allowed: {', '.join(sorted(vocab.LEVELS))}")
        return value

    @field_validator("time_preference")
    @classmethod
    def _check_time_preference(cls, value: str | None) -> str | None:
        if value is not None and value not in vocab.TIME_PREFERENCES:
            raise ValueError(f"unknown time preference '{value}'; allowed: {', '.join(sorted(vocab.TIME_PREFERENCES))}")
        return value

    @field_validator("meal_size")
    @classmethod
    def _check_meal_size(cls, value: str | None) -> str | None:
        if value is not None and value not in vocab.MEAL_SIZES:
            raise ValueError(f"unknown meal size '{value}'; allowed: {', '.join(sorted(vocab.MEAL_SIZES))}")
        return value

    @field_validator("meal_types")
    @classmethod
    def _check_meal_types(cls, value: list[str]) -> list[str]:
        return _unique_members(value, vocab.MEAL_TYPES, "meal type")

    @field_validator("allergies")
    @classmethod
    def _check_allergies(cls, value: list[str]) -> list[str]:
        return _unique_members(value, vocab.ALLERGENS, "allergen")


class PreferencesOut(PreferencesIn):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime


class PreferenceOption(BaseModel):
    value: str
    label: str


class PreferenceQuestion(BaseModel):
    """One question on the preferences form. The form renders these generically."""

    id: str
    label: str
    # Which PreferencesIn field the answer is stored in; `key` selects the entry inside nutrient_levels.
    field: Literal["nutrient_levels", "time_preference", "meal_types", "meal_size", "allergies"]
    key: str | None = None
    type: Literal["single", "multi"]
    options: list[PreferenceOption]
    help: str | None = None


class PreferenceOptions(BaseModel):
    questions: list[PreferenceQuestion]


# --- Store pricing ---------------------------------------------------------


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str = "kroger"
    location_id: str
    name: str
    chain: str | None
    address_line: str | None
    city: str | None
    state: str | None
    zip_code: str | None


class PricingStatus(BaseModel):
    configured: bool
    provider: str
    store: StoreOut | None


class SetStoreRequest(BaseModel):
    location_id: str = Field(pattern=r"^[A-Za-z0-9]{8}$", description="8-character Kroger locationId")


class ProductOut(BaseModel):
    description: str
    brand: str | None
    size_text: str | None
    package_price: float
    regular_price: float | None
    promo_price: float | None
    on_sale: bool
    sold_by_weight: bool
    product_url: str | None
    image_url: str | None
    fetched_at: datetime


class LineCostOut(BaseModel):
    position: int
    ingredient_id: int
    name: str
    quantity: float | None
    unit: str | None
    status: Literal["priced", "not_purchased", "unmeasured", "no_match", "needs_conversion"]
    reason: str | None
    is_pantry_staple: bool
    product: ProductOut | None
    used_cost: float | None
    packages: int | None
    shopping_cost: float | None


class RecipeCostOut(BaseModel):
    recipe_id: int
    servings: int
    currency: str = "USD"
    store: StoreOut
    recipe_cost: float
    cost_per_serving: float
    shopping_total: float
    pantry_staples_cost: float
    unpriced_count: int
    is_complete: bool
    oldest_price_at: datetime | None
    lines: list[LineCostOut]
