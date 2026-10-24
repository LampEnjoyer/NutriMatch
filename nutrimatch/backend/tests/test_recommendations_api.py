import pytest
from sqlalchemy import select

from app.models import Ingredient, NutritionFacts, Recipe, RecipeIngredient

URL = "/api/v1/recommendations"


def _set_preferences(client, **preferences):
    assert client.put("/api/v1/preferences", json=preferences).status_code == 200


def _recipes_with_allergen(db, allergen):
    ids = set()
    rows = db.execute(
        select(RecipeIngredient.recipe_id, Ingredient.allergens).join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
    )
    for recipe_id, allergens in rows:
        if allergen in allergens:
            ids.add(recipe_id)
    return ids


def _add_nutrition(db, per_recipe):
    for recipe_id, protein in per_recipe.items():
        db.add(NutritionFacts(recipe_id=recipe_id, serving_basis="per_serving", protein_g=protein, data_source="test"))
    db.commit()


def test_without_preferences_every_recipe_is_returned_unranked(client):
    body = client.get(f"{URL}?limit=100").json()
    assert body["total"] == 22
    assert body["excluded_for_allergies"] == 0
    assert body["ranked_by"] == [] and body["ignored_preferences"] == []
    assert all(item["score"] == 0 and item["components"] == [] for item in body["items"])
    titles = [item["title"] for item in body["items"]]
    assert titles == sorted(titles)


def test_allergies_remove_recipes_that_contain_the_allergen(client, seeded_db):
    # The sample catalog has dairy in several recipes, so this must remove something.
    expected = _recipes_with_allergen(seeded_db, "milk")
    assert 0 < len(expected) < 22
    _set_preferences(client, allergies=["milk"])

    body = client.get(f"{URL}?limit=100").json()
    assert body["excluded_for_allergies"] == len(expected)
    assert body["total"] == 22 - len(expected)
    assert {item["id"] for item in body["items"]}.isdisjoint(expected)


def test_nutrition_rows_are_picked_up_and_drive_the_order(client, seeded_db):
    ids = [r.id for r in seeded_db.scalars(select(Recipe).order_by(Recipe.id).limit(3))]
    _add_nutrition(seeded_db, {ids[0]: 10, ids[1]: 40, ids[2]: 25})
    _set_preferences(client, nutrient_levels={"protein": "high"})

    body = client.get(f"{URL}?limit=100").json()
    assert body["ranked_by"] == ["protein"]
    items = body["items"]
    assert items[0]["id"] == ids[1]
    assert items[-1]["id"] == ids[0]
    assert items[0]["components"][0]["known"] is True and items[0]["components"][0]["score"] > 0.5
    # Recipes without nutrition get the neutral score and are marked unknown, so they rank between the extremes.
    unknown = [i for i in items if i["id"] not in ids]
    assert len(unknown) == 19
    assert all(i["components"][0] == {"key": "protein", "score": 0.5, "known": False} for i in unknown)

    _set_preferences(client, nutrient_levels={"protein": "low"})
    low = client.get(f"{URL}?limit=100").json()["items"]
    assert low[0]["id"] == ids[0]
    assert low[-1]["id"] == ids[1]


def test_preference_with_no_data_is_reported_as_ignored(client):
    _set_preferences(client, nutrient_levels={"protein": "high", "fat": "no_preference"}, time_preference="short")
    body = client.get(f"{URL}?limit=100").json()
    # The sample recipes have times but no nutrition, so only time can shape the order.
    assert body["ranked_by"] == ["time"]
    assert body["ignored_preferences"] == ["protein"]


def test_meal_type_preference_puts_matching_recipes_first(client):
    _set_preferences(client, meal_types=["breakfast"])
    body = client.get(f"{URL}?limit=100").json()
    assert body["ranked_by"] == ["meal_type"]
    scores = [item["score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)
    assert body["items"][0]["meal_type"] == "breakfast"


def test_flags_match_the_recipe_detail_endpoint(client):
    items = client.get(f"{URL}?limit=100").json()["items"]
    for item in items[:8]:
        detail = client.get(f"/api/v1/recipes/{item['id']}").json()
        assert item["unreviewed_ingredients"] == detail["unreviewed_ingredients"]
        assert item["allergy_info_complete"] == detail["allergy_info_complete"]
    assert any(item["unreviewed_ingredients"] for item in items)


def test_pagination_slices_the_ranked_list_without_overlap(client):
    _set_preferences(client, meal_size="family")
    everything = client.get(f"{URL}?limit=100").json()["items"]
    first = client.get(f"{URL}?limit=5&offset=0").json()
    second = client.get(f"{URL}?limit=5&offset=5").json()
    assert first["total"] == second["total"] == 22
    assert [i["id"] for i in first["items"] + second["items"]] == [i["id"] for i in everything[:10]]


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=x"])
def test_rejects_bad_pagination(client, query):
    assert client.get(f"{URL}?{query}").status_code == 422


def _ids_matching(db, *words):
    """Recipes whose title or description contains every word, ignoring case."""
    ids = set()
    for recipe in db.scalars(select(Recipe)):
        text = f"{recipe.title} {recipe.description or ''}".lower()
        if all(word in text for word in words):
            ids.add(recipe.id)
    return ids


def test_search_matches_titles_ignoring_case(client, seeded_db):
    expected = _ids_matching(seeded_db, "alfredo")
    assert len(expected) >= 3

    for query in ("alfredo", "ALFREDO", "Alfredo"):
        body = client.get(URL, params={"q": query, "limit": 100}).json()
        assert {item["id"] for item in body["items"]} == expected
        assert body["total"] == len(expected)
        assert all("alfredo" in item["title"].lower() for item in body["items"])


def test_search_requires_every_word_in_any_order(client, seeded_db):
    both = _ids_matching(seeded_db, "chicken", "alfredo")
    assert len(both) >= 3
    for query in ("chicken alfredo", "alfredo chicken", "  chicken   alfredo "):
        body = client.get(URL, params={"q": query, "limit": 100}).json()
        assert {item["id"] for item in body["items"]} == both


def test_search_also_matches_the_description(client, seeded_db):
    recipe = seeded_db.scalars(select(Recipe).where(Recipe.description.is_not(None))).first()
    word = next(w for w in recipe.description.lower().replace(",", " ").replace(".", " ").split()
                if len(w) > 5 and w not in recipe.title.lower())
    expected = _ids_matching(seeded_db, word)
    body = client.get(URL, params={"q": word, "limit": 100}).json()
    assert recipe.id in {item["id"] for item in body["items"]}
    assert {item["id"] for item in body["items"]} == expected


def test_search_with_no_match_returns_an_empty_list(client):
    body = client.get(URL, params={"q": "zzzznotarecipe"}).json()
    assert body["items"] == [] and body["total"] == 0


@pytest.mark.parametrize("query", ["%", "_", "100%", "a_b", "\\"])
def test_search_treats_wildcard_characters_literally(client, query):
    assert client.get(URL, params={"q": query}).json()["total"] == 0


@pytest.mark.parametrize("query", ["", "   "])
def test_blank_search_is_the_same_as_no_search(client, query):
    assert client.get(URL, params={"q": query}).json()["total"] == 22


def test_search_longer_than_100_characters_is_rejected(client):
    assert client.get(URL, params={"q": "a" * 101}).status_code == 422


def test_search_narrows_the_pool_before_allergy_filtering_and_ranking(client, seeded_db):
    matches = _ids_matching(seeded_db, "alfredo")
    with_milk = matches & _recipes_with_allergen(seeded_db, "milk")
    _set_preferences(client, allergies=["milk"], meal_types=["dinner"])

    body = client.get(URL, params={"q": "alfredo", "limit": 100}).json()
    # Only recipes that matched the search can be counted as hidden by an allergy.
    assert body["excluded_for_allergies"] == len(with_milk)
    assert body["total"] == len(matches) - len(with_milk)
    assert {item["id"] for item in body["items"]} == matches - with_milk


def test_search_results_are_still_ranked_by_preferences(client):
    _set_preferences(client, meal_size="family")
    body = client.get(URL, params={"q": "a", "limit": 100}).json()
    assert body["ranked_by"] == ["meal_size"]
    scores = [item["score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)


def test_search_paginates(client):
    everything = client.get(URL, params={"q": "a", "limit": 100}).json()
    first = client.get(URL, params={"q": "a", "limit": 3, "offset": 0}).json()
    second = client.get(URL, params={"q": "a", "limit": 3, "offset": 3}).json()
    assert first["total"] == second["total"] == everything["total"]
    assert [i["id"] for i in first["items"] + second["items"]] == [i["id"] for i in everything["items"][:6]]
