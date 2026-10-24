import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.deps import get_current_user
from app.db import get_db
from app.main import create_app


def test_health_reports_recipe_count(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "recipes": 22}


def test_list_recipes_is_sorted_and_counts_all(client):
    response = client.get("/api/v1/recipes")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 22
    titles = [item["title"] for item in body["items"]]
    assert titles == sorted(titles)


def test_list_recipes_paginates(client):
    first = client.get("/api/v1/recipes?limit=5&offset=0").json()
    second = client.get("/api/v1/recipes?limit=5&offset=5").json()
    assert len(first["items"]) == 5
    assert len(second["items"]) == 5
    first_ids = {item["id"] for item in first["items"]}
    second_ids = {item["id"] for item in second["items"]}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=abc"])
def test_list_recipes_rejects_bad_pagination(client, query):
    assert client.get(f"/api/v1/recipes?{query}").status_code == 422


def test_recipe_detail_includes_ingredients_in_order(client):
    listing = client.get("/api/v1/recipes?limit=100").json()["items"]
    recipe_id = None
    for item in listing:
        if item["slug"] == "classic-chicken-fettuccine-alfredo":
            recipe_id = item["id"]
    assert recipe_id is not None

    response = client.get(f"/api/v1/recipes/{recipe_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["total_time_min"] == 35
    assert body["ingredients_complete"] is True
    assert body["ingredients"][0]["normalized_name"] == "fettuccine"
    assert body["ingredients"][0]["quantity"] == 12
    assert body["ingredients"][0]["unit"] == "oz"
    assert len(body["instructions"]) == 6


def test_to_taste_ingredient_has_null_quantity(client):
    listing = client.get("/api/v1/recipes?limit=100").json()["items"]
    curry_id = None
    for item in listing:
        if item["slug"] == "chickpea-spinach-curry":
            curry_id = item["id"]

    body = client.get(f"/api/v1/recipes/{curry_id}").json()
    cilantro = None
    for line in body["ingredients"]:
        if line["normalized_name"] == "cilantro":
            cilantro = line
    assert cilantro is not None
    assert cilantro["quantity"] is None
    assert cilantro["unit"] is None
    assert cilantro["is_optional"] is True


def test_missing_recipe_returns_404(client):
    response = client.get("/api/v1/recipes/99999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Recipe 99999 not found"}


def test_non_integer_recipe_id_returns_422(client):
    assert client.get("/api/v1/recipes/abc").status_code == 422


def test_database_errors_return_503_without_leaking_details():
    application = create_app()

    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("disk I/O error at /secret/path"))

        def close(self):
            pass

    def broken_db():
        yield BrokenSession()

    application.dependency_overrides[get_db] = broken_db
    with TestClient(application) as test_client:
        response = test_client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database error. Please try again."}
    assert "secret" not in response.text


def test_current_user_errors_clearly_when_demo_user_missing(db):
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db)
    assert exc_info.value.status_code == 503
    assert "seed" in exc_info.value.detail
