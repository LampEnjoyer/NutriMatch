import pytest

from app.ranking import (
    IngredientInfo,
    RankingPreferences,
    RecipeFeatures,
    percentiles,
    rank_recipes,
)


def ing(name="flour", allergens=(), reviewed=True):
    return IngredientInfo(name, frozenset(allergens), reviewed)


def recipe(id, title=None, *, ingredients=(), nutrients=None, time=None, servings=4, meal_type=None, complete=True):
    return RecipeFeatures(
        id=id,
        title=title or f"Recipe {id:03d}",
        meal_type=meal_type,
        total_time_min=time,
        servings=servings,
        nutrients=nutrients or {},
        ingredients=list(ingredients) or [ing()],
        ingredients_complete=complete,
    )


def order(result):
    return [r.recipe.id for r in result.ranked]


def score_of(result, recipe_id):
    return next(r for r in result.ranked if r.recipe.id == recipe_id)


def test_percentiles_share_the_midpoint_for_ties():
    assert percentiles({1: 10, 2: 20, 3: 20, 4: 30}) == {1: 0.125, 2: 0.5, 3: 0.5, 4: 0.875}


def test_percentiles_ignore_unknown_and_are_neutral_without_information():
    assert percentiles({1: 7, 2: None}) == {1: 0.5}
    assert percentiles({1: 5, 2: 5, 3: 5}) == {1: 0.5, 2: 0.5, 3: 0.5}
    assert percentiles({1: None}) == {}


def test_allergen_match_excludes_the_recipe_and_is_counted():
    recipes = [
        recipe(1, ingredients=[ing("peanut butter", ["peanut"])]),
        recipe(2, ingredients=[ing("rice")]),
    ]
    result = rank_recipes(recipes, RankingPreferences(allergies=frozenset({"peanut"})))
    assert order(result) == [2]
    assert result.excluded_for_allergies == 1


def test_unreviewed_ingredient_without_the_allergen_stays_and_is_flagged():
    recipes = [recipe(1, ingredients=[ing("rice"), ing("margarine", reviewed=False), ing("margarine", reviewed=False)])]
    result = rank_recipes(recipes, RankingPreferences(allergies=frozenset({"peanut"})))
    assert order(result) == [1]
    ranked = result.ranked[0]
    assert ranked.unreviewed_ingredients == ("margarine",)
    assert ranked.allergy_info_complete is False


def test_unreviewed_ingredient_that_lists_the_allergen_is_still_excluded():
    soup = ing("cream of mushroom soup", ["milk", "wheat"], reviewed=False)
    result = rank_recipes([recipe(1, ingredients=[soup])], RankingPreferences(allergies=frozenset({"milk"})))
    assert order(result) == []


def test_incomplete_ingredient_list_is_never_reported_allergy_complete():
    result = rank_recipes([recipe(1, complete=False)], RankingPreferences())
    assert result.ranked[0].allergy_info_complete is False
    assert rank_recipes([recipe(1)], RankingPreferences()).ranked[0].allergy_info_complete is True


def test_high_and_low_nutrient_levels_order_in_opposite_directions():
    recipes = [recipe(i, nutrients={"protein": p}) for i, p in [(1, 10), (2, 30), (3, 20)]]
    high = rank_recipes(recipes, RankingPreferences(nutrient_levels={"protein": "high"}))
    low = rank_recipes(recipes, RankingPreferences(nutrient_levels={"protein": "low"}))
    assert order(high) == [2, 3, 1]
    assert order(low) == [1, 3, 2]
    assert high.ranked_by == ["protein"]


def test_the_same_recipe_scores_by_where_it_falls_in_the_pool_not_by_a_fixed_threshold():
    prefs = RankingPreferences(nutrient_levels={"protein": "high"})
    strong_pool = [recipe(1, nutrients={"protein": 20}), recipe(2, nutrients={"protein": 5})]
    weak_pool = [recipe(1, nutrients={"protein": 20}), recipe(2, nutrients={"protein": 90})]
    assert score_of(rank_recipes(strong_pool, prefs), 1).score > 0.5
    assert score_of(rank_recipes(weak_pool, prefs), 1).score < 0.5


def test_excluded_recipes_do_not_influence_the_percentiles_of_the_rest():
    prefs = RankingPreferences(nutrient_levels={"protein": "high"}, allergies=frozenset({"peanut"}))
    recipes = [
        recipe(1, nutrients={"protein": 200}, ingredients=[ing("peanut", ["peanut"])]),
        recipe(2, nutrients={"protein": 10}),
        recipe(3, nutrients={"protein": 20}),
    ]
    result = rank_recipes(recipes, prefs)
    assert score_of(result, 3).score == 0.75
    assert score_of(result, 2).score == 0.25


def test_missing_value_is_neutral_and_marked_unknown():
    recipes = [
        recipe(1, nutrients={"protein": 10}),
        recipe(2, nutrients={"protein": 30}),
        recipe(3),
    ]
    result = rank_recipes(recipes, RankingPreferences(nutrient_levels={"protein": "high"}))
    assert order(result) == [2, 3, 1]
    unknown = score_of(result, 3)
    assert unknown.score == 0.5
    assert unknown.components[0].known is False
    assert score_of(result, 2).components[0].known is True


def test_a_preference_with_no_data_anywhere_is_reported_as_ignored():
    recipes = [recipe(2, "B"), recipe(1, "A")]
    result = rank_recipes(recipes, RankingPreferences(nutrient_levels={"protein": "high"}, time_preference="short"))
    assert result.ranked_by == []
    assert result.ignored == ["protein", "time"]
    assert order(result) == [1, 2]  # no signal, so title order


def test_dont_care_is_not_an_active_preference():
    recipes = [recipe(1, nutrients={"protein": 1}), recipe(2, nutrients={"protein": 2})]
    result = rank_recipes(recipes, RankingPreferences(nutrient_levels={"protein": "no_preference"}))
    assert result.ranked_by == [] and result.ignored == []
    assert all(r.score == 0 and r.components == () for r in result.ranked)


@pytest.mark.parametrize(
    ("preference", "expected"),
    [("short", [1, 2, 3, 4, 5]), ("long", [5, 4, 3, 2, 1]), ("medium", [3, 2, 4, 1, 5])],
)
def test_time_preference_picks_the_matching_end_of_the_range(preference, expected):
    recipes = [recipe(i, time=t) for i, t in [(1, 10), (2, 20), (3, 30), (4, 40), (5, 50)]]
    result = rank_recipes(recipes, RankingPreferences(time_preference=preference))
    assert order(result) == expected


def test_meal_type_prefers_matches_and_treats_unlabelled_as_neutral():
    recipes = [
        recipe(1, meal_type="dinner"),
        recipe(2, meal_type="breakfast"),
        recipe(3, meal_type=None),
        recipe(4, meal_type="lunch"),
    ]
    result = rank_recipes(recipes, RankingPreferences(meal_types=("breakfast", "lunch")))
    assert order(result) == [2, 4, 3, 1]
    assert score_of(result, 3).score == 0.5


def test_solo_prefers_fewer_servings_and_family_prefers_more():
    recipes = [recipe(1, servings=1), recipe(2, servings=4), recipe(3, servings=12)]
    assert order(rank_recipes(recipes, RankingPreferences(meal_size="solo"))) == [1, 2, 3]
    assert order(rank_recipes(recipes, RankingPreferences(meal_size="family"))) == [3, 2, 1]


def test_score_is_the_weighted_average_of_active_preferences():
    recipes = [
        recipe(1, nutrients={"protein": 10}, meal_type="dinner"),
        recipe(2, nutrients={"protein": 30}, meal_type="lunch"),
    ]
    prefs = RankingPreferences(nutrient_levels={"protein": "high"}, meal_types=("dinner",))
    equal = rank_recipes(recipes, prefs)
    # recipe 1: protein 0.25, meal 1.0 -> 0.625; recipe 2: protein 0.75, meal 0.0 -> 0.375
    assert score_of(equal, 1).score == pytest.approx(0.625)
    assert score_of(equal, 2).score == pytest.approx(0.375)

    protein_heavy = rank_recipes(recipes, prefs, weights={"protein": 3.0, "meal_type": 1.0})
    assert score_of(protein_heavy, 2).score == pytest.approx((3 * 0.75 + 0) / 4)
    assert order(protein_heavy) == [2, 1]


def test_scores_stay_between_zero_and_one():
    recipes = [recipe(i, nutrients={"protein": i, "fat": 10 - i, "calories": i * i}, time=i, servings=i, meal_type="dinner") for i in range(1, 8)]
    prefs = RankingPreferences(
        nutrient_levels={"protein": "high", "fat": "low", "calories": "high"},
        time_preference="medium", meal_types=("dinner",), meal_size="family",
    )
    for ranked in rank_recipes(recipes, prefs).ranked:
        assert 0 <= ranked.score <= 1


def test_ties_break_on_title_then_id_so_order_is_stable():
    recipes = [recipe(3, "Beta"), recipe(1, "Beta"), recipe(2, "Alpha")]
    assert order(rank_recipes(recipes, RankingPreferences())) == [2, 1, 3]
