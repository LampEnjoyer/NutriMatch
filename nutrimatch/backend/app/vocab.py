"""Controlled vocabularies (constants)"""

MASS_UNITS = frozenset({"g", "kg", "oz", "lb"})
VOLUME_UNITS = frozenset({"ml", "l", "tsp", "tbsp", "cup", "fl_oz"})
# Count units need an ingredient-specific gram weight before they can be converted.
COUNT_UNITS = frozenset({"piece", "clove", "slice", "pinch"})
ALL_UNITS = MASS_UNITS | VOLUME_UNITS | COUNT_UNITS

# The nine major US food allergens, plus gluten (which also covers barley and rye).
ALLERGENS = frozenset(
    {"milk", "egg", "fish", "shellfish", "tree_nut", "peanut", "wheat", "soy", "sesame", "gluten"}
)

# What kind of animal product an ingredient is, if any. Drives dietary-restriction filtering.
ANIMAL_CATEGORIES = frozenset({"none", "dairy", "egg", "meat", "poultry", "fish", "shellfish", "honey"})

DIETS = frozenset({"vegetarian", "vegan", "pescatarian", "gluten_free", "dairy_free"})

MEAL_TYPES = frozenset({"breakfast", "lunch", "dinner", "snack"})

# Nutrients a user can state a preference for, and the levels they can choose. Adding a nutrient
# (carbohydrates, sodium, ...) here and in preference_options.py needs no schema change.
NUTRIENT_KEYS = frozenset({"protein", "fat", "calories"})
LEVELS = frozenset({"low", "high", "no_preference"})

TIME_PREFERENCES = frozenset({"short", "medium", "long"})

# Who the meal is for. Maps to recipe servings when ranking (solo: few servings, family: many).
MEAL_SIZES = frozenset({"solo", "family"})

SERVING_BASES = frozenset({"per_serving", "per_recipe"})
