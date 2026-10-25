"""Ranks recipes against a user's preferences.

Two stages:

1. Hard filter on allergens.
   An ingredient whose allergen data is unreviewed is NOT treated as a match for allergens it does not
   list (we cannot know), so those recipes stay in and are flagged for the user to check.
2. Soft ranking. Each active preference becomes a score from 0 to 1, and a recipe's score is the
   weighted average of those. "Active" means the user chose something other than "don't care".
"""

from bisect import bisect_left, bisect_right
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

# Relative importance of each preference. Equal until there is evidence for anything else.
WEIGHTS: Mapping[str, float] = {
    "protein": 1.0,
    "fat": 1.0,
    "calories": 1.0,
    "time": 1.0,
    "meal_type": 1.0,
    "meal_size": 1.0,
}

NEUTRAL = 0.5

# Scores are rounded so mathematically equal scores compare equal despite floating-point noise.
SCORE_DECIMALS = 9


@dataclass(frozen=True)
class IngredientInfo:
    name: str
    allergens: frozenset[str]
    allergens_reviewed: bool


@dataclass(frozen=True)
class RecipeFeatures:
    id: int
    title: str
    meal_type: str | None
    total_time_min: float | None
    servings: int
    # Per-serving nutrient values keyed by vocab.NUTRIENT_KEYS; None or absent when unknown.
    nutrients: Mapping[str, float | None]
    ingredients: Sequence[IngredientInfo]
    ingredients_complete: bool = True


@dataclass(frozen=True)
class RankingPreferences:
    nutrient_levels: Mapping[str, str] = field(default_factory=dict)
    time_preference: str | None = None
    meal_types: Sequence[str] = ()
    meal_size: str | None = None
    allergies: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Component:
    key: str
    score: float
    # False when this recipe had no value, so `score` is the neutral placeholder.
    known: bool


@dataclass(frozen=True)
class Ranked:
    recipe: RecipeFeatures
    score: float
    components: tuple[Component, ...]
    unreviewed_ingredients: tuple[str, ...]
    allergy_info_complete: bool


@dataclass(frozen=True)
class RankingResult:
    ranked: list[Ranked]
    excluded_for_allergies: int
    # Preferences that shaped the order, and those that could not be applied for lack of data.
    ranked_by: list[str]
    ignored: list[str]


def contains_allergen(recipe: RecipeFeatures, allergies: frozenset[str]) -> bool:
    return any(ingredient.allergens & allergies for ingredient in recipe.ingredients)


def unreviewed_ingredients(recipe: RecipeFeatures) -> tuple[str, ...]:
    # Each name once, in recipe order, even if the recipe lists it on several lines.
    return tuple(dict.fromkeys(i.name for i in recipe.ingredients if not i.allergens_reviewed))


def percentiles(values: Mapping[int, float | None]) -> dict[int, float]:
    """Percentile rank (0 to 1) of each known value among all known values. Ties share their midpoint.

    A single known value, or all values equal, gives 0.5 for everyone: no information, so neutral.
    """
    known = {key: value for key, value in values.items() if value is not None}
    ordered = sorted(known.values())
    total = len(ordered)
    result = {}
    for key, value in known.items():
        below = bisect_left(ordered, value)
        equal = bisect_right(ordered, value) - below
        result[key] = (below + equal / 2) / total
    return result


Shape = Callable[[float], float]


def _prefer(high: bool) -> Shape:
    """Higher percentile scores higher when `high`, lower percentile scores higher otherwise."""
    return (lambda p: p) if high else (lambda p: 1 - p)


def _prefer_middle(percentile: float) -> float:
    return 1 - abs(percentile - NEUTRAL) * 2


def _scores(pool: Sequence[RecipeFeatures], values: Mapping[int, float | None], shape: Shape) -> dict[int, float | None]:
    """Score every recipe in the pool from its percentile, or return nothing when no recipe has a value."""
    ranks = percentiles(values)
    if not ranks:
        return {}
    return {r.id: (shape(ranks[r.id]) if r.id in ranks else None) for r in pool}


def rank_recipes(
    recipes: Sequence[RecipeFeatures],
    preferences: RankingPreferences,
    weights: Mapping[str, float] = WEIGHTS,
) -> RankingResult:
    pool = [r for r in recipes if not contains_allergen(r, preferences.allergies)]
    excluded = len(recipes) - len(pool)

    # key -> {recipe id -> score, or None when that recipe has no value}. Empty means not applicable.
    scorers: dict[str, dict[int, float | None]] = {}
    ignored: list[str] = []

    def add(key: str, scores: dict[int, float | None]) -> None:
        if scores:
            scorers[key] = scores
        else:
            ignored.append(key)

    for nutrient, level in preferences.nutrient_levels.items():
        if level not in ("low", "high"):
            continue
        values = {r.id: r.nutrients.get(nutrient) for r in pool}
        add(nutrient, _scores(pool, values, _prefer(level == "high")))

    if preferences.time_preference is not None:
        values = {r.id: r.total_time_min for r in pool}
        shape = {"short": _prefer(False), "medium": _prefer_middle, "long": _prefer(True)}[preferences.time_preference]
        add("time", _scores(pool, values, shape))

    if preferences.meal_size is not None:
        values = {r.id: float(r.servings) for r in pool}
        add("meal_size", _scores(pool, values, _prefer(preferences.meal_size == "family")))

    if len(preferences.meal_types) > 0:
        wanted = set(preferences.meal_types)
        add("meal_type", {r.id: (None if r.meal_type is None else float(r.meal_type in wanted)) for r in pool})

    ranked = []
    for recipe in pool:
        components = []
        for key, scores in scorers.items():
            score = scores.get(recipe.id)
            components.append(Component(key, NEUTRAL if score is None else score, known=score is not None))
        total_weight = sum(weights[c.key] for c in components)
        score = sum(weights[c.key] * c.score for c in components) / total_weight if total_weight > 0 else 0.0
        score = round(score, SCORE_DECIMALS)
        unreviewed = unreviewed_ingredients(recipe)
        ranked.append(Ranked(
            recipe=recipe,
            score=score,
            components=tuple(components),
            unreviewed_ingredients=unreviewed,
            allergy_info_complete=recipe.ingredients_complete and len(unreviewed) == 0,
        ))

    # Ties break on title then id so the order is stable between requests.
    ranked.sort(key=lambda r: (-r.score, r.recipe.title, r.recipe.id))
    return RankingResult(ranked=ranked, excluded_for_allergies=excluded, ranked_by=list(scorers), ignored=ignored)
