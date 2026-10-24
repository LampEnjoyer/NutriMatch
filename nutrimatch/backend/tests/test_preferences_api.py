import pytest

from app import vocab


def test_options_describe_every_question(client):
    body = client.get("/api/v1/preferences/options").json()
    questions = {q["id"]: q for q in body["questions"]}
    assert list(questions) == ["protein", "fat", "calories", "time", "meal_types", "meal_size", "allergies"]

    protein = questions["protein"]
    assert (protein["field"], protein["key"], protein["type"]) == ("nutrient_levels", "protein", "single")
    assert [o["value"] for o in protein["options"]] == ["low", "high", "no_preference"]
    assert protein["options"][2]["label"] == "Don't care"

    assert [o["value"] for o in questions["time"]["options"]] == ["short", "medium", "long"]
    assert [o["value"] for o in questions["meal_types"]["options"]] == ["breakfast", "lunch", "dinner"]
    assert [o["value"] for o in questions["meal_size"]["options"]] == ["solo", "family"]
    assert questions["allergies"]["type"] == "multi"
    assert "unverified" in questions["allergies"]["help"]


def test_every_offered_option_is_accepted_by_the_api(client):
    # The form is generated from /options, so anything it offers must pass validation.
    questions = client.get("/api/v1/preferences/options").json()["questions"]
    for question in questions:
        for option in question["options"]:
            value = option["value"]
            if question["field"] == "nutrient_levels":
                body = {"nutrient_levels": {question["key"]: value}}
            elif question["type"] == "multi":
                body = {question["field"]: [value]}
            else:
                body = {question["field"]: value}
            assert client.put("/api/v1/preferences", json=body).status_code == 200, body


def test_every_allergen_in_the_vocabulary_is_offered(client):
    questions = {q["id"]: q for q in client.get("/api/v1/preferences/options").json()["questions"]}
    assert {o["value"] for o in questions["allergies"]["options"]} == vocab.ALLERGENS


def test_new_user_has_empty_preferences(client):
    body = client.get("/api/v1/preferences").json()
    assert body["nutrient_levels"] == {}
    assert body["time_preference"] is None
    assert body["meal_types"] == []
    assert body["meal_size"] is None
    assert body["allergies"] == []


def test_put_saves_and_get_returns_the_same_preferences(client):
    preferences = {
        "nutrient_levels": {"protein": "high", "fat": "low", "calories": "no_preference"},
        "time_preference": "short",
        "meal_types": ["dinner", "lunch"],
        "meal_size": "family",
        "allergies": ["peanut", "shellfish"],
    }
    put = client.put("/api/v1/preferences", json=preferences)
    assert put.status_code == 200
    saved = client.get("/api/v1/preferences").json()
    for key, value in preferences.items():
        assert saved[key] == value
    assert put.json()["updated_at"] == saved["updated_at"]


def test_put_replaces_everything_so_omitted_fields_are_cleared(client):
    client.put("/api/v1/preferences", json={"time_preference": "long", "allergies": ["milk"], "meal_size": "solo"})
    client.put("/api/v1/preferences", json={"allergies": ["soy"]})
    saved = client.get("/api/v1/preferences").json()
    assert saved["allergies"] == ["soy"]
    assert saved["time_preference"] is None
    assert saved["meal_size"] is None


def test_put_removes_duplicate_list_entries_keeping_order(client):
    saved = client.put(
        "/api/v1/preferences", json={"allergies": ["soy", "milk", "soy"], "meal_types": ["lunch", "lunch"]}
    ).json()
    assert saved["allergies"] == ["soy", "milk"]
    assert saved["meal_types"] == ["lunch"]


@pytest.mark.parametrize(
    "body",
    [
        {"nutrient_levels": {"protein": "extreme"}},
        {"nutrient_levels": {"sodium": "low"}},
        {"time_preference": "instant"},
        {"meal_size": "couple"},
        {"meal_types": ["brunch"]},
        {"allergies": ["pollen"]},
        {"unknown_field": 1},
        {"allergies": "milk"},
    ],
)
def test_put_rejects_invalid_values_without_saving(client, body):
    client.put("/api/v1/preferences", json={"allergies": ["egg"]})
    assert client.put("/api/v1/preferences", json=body).status_code == 422
    assert client.get("/api/v1/preferences").json()["allergies"] == ["egg"]


def test_recipe_detail_flags_unreviewed_ingredients(client):
    recipes = client.get("/api/v1/recipes?limit=100").json()["items"]
    flagged = complete = None
    for item in recipes:
        detail = client.get(f"/api/v1/recipes/{item['id']}").json()
        if detail["unreviewed_ingredients"] and flagged is None:
            flagged = detail
        if not detail["unreviewed_ingredients"] and complete is None:
            complete = detail
    assert flagged is not None and complete is not None

    assert flagged["allergy_info_complete"] is False
    names = {line["name"] for line in flagged["ingredients"] if not line["allergens_reviewed"]}
    assert set(flagged["unreviewed_ingredients"]) == names
    assert len(flagged["unreviewed_ingredients"]) == len(names)  # listed once each

    assert complete["allergy_info_complete"] is True
    for line in complete["ingredients"]:
        assert line["allergens_reviewed"] is True
        assert isinstance(line["allergens"], list)
