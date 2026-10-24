"""SQLAlchemy models.

Follows spec section 8, with these additions:
- Ingredient.allergens / animal_category / allergens_reviewed: needed so allergies and diets
  can be hard filters, and so an ingredient whose allergens nobody has reviewed is treated
  as "unknown" rather than "safe".
- Recipe.slug (stable seed/import key) and Recipe.inactive_time_min (e.g. overnight chilling,
  shown separately so "5 minute" overnight oats don't pass as a quick breakfast unannounced).
- RecipeIngredient.position / is_optional.
- Recipe.ingredients_complete: False when some ingredient lines could not be structured
  (e.g. an import with free-text measures). Such recipes are never reported allergy-safe.
- UserPreferences: coarse levels (nutrient_levels, time_preference, meal_types, meal_size) instead of
  numeric targets. Allergies are the only hard filter.
- User.timezone: so daily nutrition totals use the user's calendar day.
- MealLog.meal_slot, GroceryListItem.notes / source_recipe_ids.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    preferences: Mapped["UserPreferences | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Soft preferences, keyed by nutrient (see vocab.NUTRIENT_KEYS) with a level from vocab.LEVELS.
    # A missing key means no preference. A JSON map so a new nutrient needs no migration.
    nutrient_levels: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    time_preference: Mapped[str | None] = mapped_column(String(16))
    meal_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    meal_size: Mapped[str | None] = mapped_column(String(16))

    # Lists of vocabulary values (see app.vocab) or ingredient normalized names.
    # Allergies are the only hard filter; everything above only influences ranking.
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    dietary_preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    avoided_ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="preferences")


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint("servings > 0", name="ck_recipes_servings_positive"),
        CheckConstraint("preparation_time_min >= 0", name="ck_recipes_prep_nonnegative"),
        CheckConstraint("cooking_time_min >= 0", name="ck_recipes_cook_nonnegative"),
        CheckConstraint("inactive_time_min >= 0", name="ck_recipes_inactive_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable identifier from the seed file / import source, so re-seeding is idempotent.
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    cuisine: Mapped[str | None] = mapped_column(String(50), index=True)
    meal_type: Mapped[str | None] = mapped_column(String(20), index=True)
    preparation_time_min: Mapped[int | None] = mapped_column(Integer)
    cooking_time_min: Mapped[int | None] = mapped_column(Integer)
    # Hands-off waiting (chilling, marinating, rising). Not counted in total_time_min, but shown.
    inactive_time_min: Mapped[int | None] = mapped_column(Integer)
    servings: Mapped[int] = mapped_column(Integer)
    instructions: Mapped[list[str]] = mapped_column(JSON, default=list)
    image_url: Mapped[str | None] = mapped_column(String(500))
    source_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(500))
    ingredients_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeIngredient.position"
    )
    nutrition: Mapped[list["NutritionFacts"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )

    @property
    def total_time_min(self) -> int | None:
        if self.preparation_time_min is None and self.cooking_time_min is None:
            return None
        prep = self.preparation_time_min if self.preparation_time_min is not None else 0
        cook = self.cooking_time_min if self.cooking_time_min is not None else 0
        return prep + cook


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    default_unit: Mapped[str | None] = mapped_column(String(16))
    # grams per millilitre; filled from FoodData Central portion data in Phase 3.
    density_g_per_ml: Mapped[float | None] = mapped_column(Float)
    # grams per piece/clove/slice; filled from FoodData Central portion data in Phase 3.
    grams_per_count: Mapped[float | None] = mapped_column(Float)
    fdc_id: Mapped[int | None] = mapped_column(Integer)

    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)
    animal_category: Mapped[str] = mapped_column(String(16), default="none")
    # False means allergens above are not known to be complete; treat as "unknown", not "safe".
    allergens_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_recipe_ingredients_quantity_positive"),
        Index("ix_recipe_ingredients_recipe_id", "recipe_id"),
        Index("ix_recipe_ingredients_ingredient_id", "ingredient_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="RESTRICT"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    # NULL quantity and unit means "to taste" / unmeasured; excluded from nutrition totals.
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(16))
    preparation_notes: Mapped[str | None] = mapped_column(String(200))
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    substitution_group: Mapped[str | None] = mapped_column(String(50))

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient] = relationship()


class NutritionFacts(Base):
    __tablename__ = "nutrition_facts"
    __table_args__ = (UniqueConstraint("recipe_id", "serving_basis", name="uq_nutrition_recipe_basis"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    serving_basis: Mapped[str] = mapped_column(String(16), default="per_serving")
    calories: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carbohydrates_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    saturated_fat_g: Mapped[float | None] = mapped_column(Float)
    fiber_g: Mapped[float | None] = mapped_column(Float)
    sugar_g: Mapped[float | None] = mapped_column(Float)
    sodium_mg: Mapped[float | None] = mapped_column(Float)
    micronutrients: Mapped[dict | None] = mapped_column(JSON)
    data_source: Mapped[str] = mapped_column(String(200))
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=True)
    # Ingredient lines that could not be included (no quantity, no conversion, no FDC match).
    excluded_ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    recipe: Mapped[Recipe] = relationship(back_populates="nutrition")


class SavedRecipe(Base):
    __tablename__ = "saved_recipes"
    __table_args__ = (UniqueConstraint("user_id", "recipe_id", name="uq_saved_recipe_user_recipe"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MealLog(Base):
    __tablename__ = "meal_logs"
    __table_args__ = (
        CheckConstraint("servings_consumed > 0", name="ck_meal_logs_servings_positive"),
        Index("ix_meal_logs_user_consumed_at", "user_id", "consumed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # SET NULL so deleting a recipe never deletes a user's history; the snapshot keeps the numbers.
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id", ondelete="SET NULL"))
    meal_slot: Mapped[str] = mapped_column(String(20))
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    servings_consumed: Mapped[float] = mapped_column(Float)
    # Copy of the recipe title and nutrition at log time, so later recipe edits don't rewrite history.
    nutrition_snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GroceryList(Base):
    __tablename__ = "grocery_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    items: Mapped[list["GroceryListItem"]] = relationship(
        back_populates="grocery_list", cascade="all, delete-orphan"
    )


class GroceryListItem(Base):
    __tablename__ = "grocery_list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    grocery_list_id: Mapped[int] = mapped_column(ForeignKey("grocery_lists.id", ondelete="CASCADE"), index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="RESTRICT"))
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(16))
    notes: Mapped[str | None] = mapped_column(String(200))
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_price: Mapped[float | None] = mapped_column(Float)
    source_recipe_ids: Mapped[list[int]] = mapped_column(JSON, default=list)

    grocery_list: Mapped[GroceryList] = relationship(back_populates="items")
    ingredient: Mapped[Ingredient] = relationship()
