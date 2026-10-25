"""Data representation of user preference options"""

from app import vocab
from app.schemas import PreferenceOption, PreferenceOptions, PreferenceQuestion

LEVEL_LABELS = {"low": "Low", "high": "High", "no_preference": "Don't care"}
TIME_LABELS = {"short": "Short", "medium": "Medium", "long": "Long"}
MEAL_TYPE_LABELS = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "snack": "Snack"}
MEAL_SIZE_LABELS = {"solo": "Just me", "family": "Family"}
ALLERGEN_LABELS = {
    "milk": "Milk", "egg": "Eggs", "fish": "Fish", "shellfish": "Shellfish", "tree_nut": "Tree nuts",
    "peanut": "Peanuts", "wheat": "Wheat", "soy": "Soy", "sesame": "Sesame", "gluten": "Gluten",
}

ALLERGY_HELP = (
    "Some ingredients have unverified allergen information. Recipes that use them are flagged, "
    "so check those labels yourself."
)


def _options(labels: dict[str, str], allowed: frozenset[str]) -> list[PreferenceOption]:
    # Keep the display order of `labels`, and never offer a value the API would reject.
    return [PreferenceOption(value=value, label=label) for value, label in labels.items() if value in allowed]


def build_options() -> PreferenceOptions:
    nutrient_questions = [
        PreferenceQuestion(
            id=nutrient, label=nutrient.capitalize(), field="nutrient_levels", key=nutrient, type="single",
            options=_options(LEVEL_LABELS, vocab.LEVELS),
        )
        for nutrient in ("protein", "fat", "calories")
        if nutrient in vocab.NUTRIENT_KEYS
    ]
    return PreferenceOptions(questions=[
        *nutrient_questions,
        PreferenceQuestion(
            id="time", label="Time to make", field="time_preference", type="single",
            options=_options(TIME_LABELS, vocab.TIME_PREFERENCES),
        ),
        PreferenceQuestion(
            id="meal_types", label="Meal", field="meal_types", type="multi",
            options=_options({k: v for k, v in MEAL_TYPE_LABELS.items() if k != "snack"}, vocab.MEAL_TYPES),
        ),
        PreferenceQuestion(
            id="meal_size", label="Cooking for", field="meal_size", type="single",
            options=_options(MEAL_SIZE_LABELS, vocab.MEAL_SIZES),
        ),
        PreferenceQuestion(
            id="allergies", label="Allergies", field="allergies", type="multi",
            options=_options(ALLERGEN_LABELS, vocab.ALLERGENS), help=ALLERGY_HELP,
        ),
    ])
