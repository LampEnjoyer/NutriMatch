"""Controlled vocabularies shared by models, seed validation and (later) API schemas.

Kept as plain frozensets so validation is an explicit membership check.
"""

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

PRIMARY_GOALS = frozenset({"high_protein", "lower_calorie", "lower_fat", "balanced"})

CARB_PREFERENCES = frozenset({"low", "moderate", "high", "no_preference"})

SERVING_BASES = frozenset({"per_serving", "per_recipe"})
