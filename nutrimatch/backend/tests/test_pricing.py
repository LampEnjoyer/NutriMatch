"""Pricing service and endpoints with a fake provider standing in for Kroger.

The fake returns parsed products exactly as KrogerClient would; prices here are test fixtures,
never shown to users.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.deps import get_price_provider
from app.models import IngredientProductMatch, Recipe
from app.pricing.kroger import KrogerError, ProductResult, StoreResult

STORE = StoreResult("01400513", "Kroger - Test Store", "KROGER", "1 Main St", "Hilliard", "OH", "43026")


def _p(product_id, description, size, regular, promo=None, sold_by="Unit"):
    return ProductResult(
        product_id=product_id,
        description=description,
        brand="Kroger",
        size_text=size,
        sold_by=sold_by,
        regular_price=regular,
        promo_price=promo,
        product_url=f"https://www.kroger.com/search?query={product_id}",
        image_url=None,
    )


CATALOG = {
    "fettuccine pasta": [
        _p("0000000000101", "Kroger Fettuccine", "16 oz", 1.99),
        _p("0000000000102", "Kroger Fettuccine Small", "8 oz", 1.49),
    ],
    "boneless skinless chicken breast": [
        _p("0000000000201", "Kroger Boneless Skinless Chicken Breasts", "2.5 lb", 9.99),
        _p("0000000000202", "Breaded Chicken Breast Fillets", "1 lb", 3.00),
    ],
    "olive oil": [
        _p("0000000000301", "Kroger Extra Virgin Olive Oil", "16.9 fl oz", 7.99),
        _p("0000000000302", "Kroger Olive Oil Cooking Spray", "5 oz", 3.49),
    ],
    "unsalted butter": [
        _p("0000000000401", "Kroger Unsalted Butter Sticks", "16 oz", 4.99),
        _p("0000000000402", "Kroger Creamy Peanut Butter", "16 oz", 2.00),
    ],
    "garlic": [_p("0000000000501", "Fresh Garlic", "3 ct", 1.99)],
    "heavy whipping cream": [_p("0000000000601", "Kroger Heavy Whipping Cream", "1 pt", 3.99)],
    "grated parmesan cheese": [_p("0000000000701", "Kroger Grated Parmesan Cheese", "8 oz", 4.49)],
    "salt": [_p("0000000000801", "Kroger Iodized Salt", "26 oz", 1.29)],
    "black pepper": [_p("0000000000901", "Kroger Ground Black Pepper", "3 oz", 3.99)],
}


class FakeProvider:
    provider_name = "kroger"

    def __init__(self, catalog=None, fail_with=None):
        self.catalog = catalog if catalog is not None else CATALOG
        self.fail_with = fail_with
        self.product_searches: list[str] = []

    def search_locations(self, zip_code, limit=10):
        if self.fail_with:
            raise self.fail_with
        return [STORE]

    def get_location(self, location_id):
        if location_id == STORE.location_id:
            return STORE
        return None

    def search_products(self, term, location_id, limit=20):
        if self.fail_with:
            raise self.fail_with
        self.product_searches.append(term)
        return list(self.catalog.get(term, []))


@pytest.fixture
def provider(client):
    fake = FakeProvider()
    client.app.dependency_overrides[get_price_provider] = lambda: fake
    return fake


def _recipe_id(db, slug):
    return db.scalar(select(Recipe.id).where(Recipe.slug == slug))


def _choose_store(client):
    response = client.put("/api/v1/preferences/store", json={"location_id": STORE.location_id})
    assert response.status_code == 200
    return response.json()


def _lines_by_name(body):
    lines = {}
    for line in body["lines"]:
        lines[line["name"]] = line
    return lines


def test_status_without_credentials(client):
    client.app.dependency_overrides[get_price_provider] = lambda: None
    body = client.get("/api/v1/pricing/status").json()
    assert body == {"configured": False, "provider": "kroger", "store": None}


def test_endpoints_explain_missing_credentials(client, seeded_db):
    client.app.dependency_overrides[get_price_provider] = lambda: None
    response = client.get("/api/v1/stores?zip_code=43026")
    assert response.status_code == 503
    assert "KROGER_CLIENT_ID" in response.json()["detail"]


def test_store_search_and_selection(client, provider):
    stores = client.get("/api/v1/stores?zip_code=43026").json()
    assert stores[0]["location_id"] == "01400513"

    saved = _choose_store(client)
    assert saved["name"] == "Kroger - Test Store"
    status = client.get("/api/v1/pricing/status").json()
    assert status["configured"] is True
    assert status["store"]["location_id"] == "01400513"


@pytest.mark.parametrize("zip_code", ["4302", "430261", "abcde"])
def test_store_search_rejects_bad_zip(client, provider, zip_code):
    assert client.get(f"/api/v1/stores?zip_code={zip_code}").status_code == 422


def test_unknown_store_is_404_and_bad_id_is_422(client, provider):
    assert client.put("/api/v1/preferences/store", json={"location_id": "99999999"}).status_code == 404
    assert client.put("/api/v1/preferences/store", json={"location_id": "short"}).status_code == 422


def test_cost_requires_a_store(client, provider, seeded_db):
    recipe_id = _recipe_id(seeded_db, "classic-chicken-fettuccine-alfredo")
    response = client.get(f"/api/v1/recipes/{recipe_id}/cost")
    assert response.status_code == 409


def test_cost_for_missing_recipe_is_404(client, provider):
    _choose_store(client)
    assert client.get("/api/v1/recipes/99999/cost").status_code == 404


def test_recipe_cost_at_recipe_servings(client, provider, seeded_db):
    _choose_store(client)
    recipe_id = _recipe_id(seeded_db, "classic-chicken-fettuccine-alfredo")
    body = client.get(f"/api/v1/recipes/{recipe_id}/cost").json()
    lines = _lines_by_name(body)

    pasta = lines["Fettuccine, dry"]
    assert pasta["status"] == "priced"
    assert pasta["product"]["description"] == "Kroger Fettuccine"  # cheaper per oz, not cheaper per box
    assert pasta["packages"] == 1
    assert pasta["used_cost"] == pytest.approx(1.49, abs=0.01)  # 12 of 16 oz at $1.99

    chicken = lines["Chicken breast, boneless skinless"]
    assert chicken["product"]["description"] == "Kroger Boneless Skinless Chicken Breasts"  # breaded excluded

    cream = lines["Heavy cream"]
    assert cream["status"] == "priced"  # cups -> pint, same dimension
    assert cream["used_cost"] == pytest.approx(2.99, abs=0.01)

    butter = lines["Butter, unsalted"]
    assert butter["status"] == "needs_conversion"  # tbsp vs oz by weight; no density yet
    assert butter["product"]["description"] == "Kroger Unsalted Butter Sticks"  # peanut butter excluded

    garlic = lines["Garlic"]
    assert garlic["status"] == "needs_conversion"  # cloves vs bulbs

    salt = lines["Salt"]
    assert salt["is_pantry_staple"] is True

    assert body["unpriced_count"] == 2  # butter and garlic; staples don't count
    assert body["is_complete"] is False
    assert body["recipe_cost"] == pytest.approx(10.50, abs=0.01)
    assert body["cost_per_serving"] == pytest.approx(2.62, abs=0.01)
    assert body["shopping_total"] == pytest.approx(28.45, abs=0.01)
    assert body["store"]["location_id"] == "01400513"
    assert body["oldest_price_at"] is not None


def test_recipe_cost_scales_with_servings(client, provider, seeded_db):
    _choose_store(client)
    recipe_id = _recipe_id(seeded_db, "classic-chicken-fettuccine-alfredo")
    body = client.get(f"/api/v1/recipes/{recipe_id}/cost?servings=8").json()
    lines = _lines_by_name(body)

    assert body["servings"] == 8
    assert lines["Fettuccine, dry"]["quantity"] == 24
    assert lines["Fettuccine, dry"]["packages"] == 2  # 24 oz needs two 16 oz boxes
    assert lines["Chicken breast, boneless skinless"]["packages"] == 1  # 2 lb fits in one 2.5 lb pack
    assert lines["Heavy cream"]["packages"] == 2  # 24 fl oz needs two pints
    assert body["recipe_cost"] == pytest.approx(21.00, abs=0.01)


@pytest.mark.parametrize("servings", ["0", "101", "two"])
def test_cost_rejects_bad_servings(client, provider, seeded_db, servings):
    _choose_store(client)
    recipe_id = _recipe_id(seeded_db, "classic-chicken-fettuccine-alfredo")
    assert client.get(f"/api/v1/recipes/{recipe_id}/cost?servings={servings}").status_code == 422


def test_lookups_are_cached_between_requests(client, provider, seeded_db):
    _choose_store(client)
    recipe_id = _recipe_id(seeded_db, "classic-chicken-fettuccine-alfredo")
    client.get(f"/api/v1/recipes/{recipe_id}/cost")
    first_count = len(provider.product_searches)
    client.get(f"/api/v1/recipes/{recipe_id}/cost")
    assert first_count == 9  # one search per distinct ingredient
    assert len(provider.product_searches) == first_count


def test_stale_lookups_search_again(client, provider, seeded_db, session_factory):
    _choose_store(client)
    recipe_id = _recipe_id(seeded_db, "classic-chicken-fettuccine-alfredo")
    client.get(f"/api/v1/recipes/{recipe_id}/cost")

    session = session_factory()
    for match in session.scalars(select(IngredientProductMatch)):
        match.searched_at = datetime.now(UTC) - timedelta(hours=25)
    session.commit()
    session.close()

    client.get(f"/api/v1/recipes/{recipe_id}/cost")
    assert len(provider.product_searches) == 18


def test_no_match_is_reported_not_guessed(client, seeded_db):
    fake = FakeProvider(catalog={})
    client.app.dependency_overrides[get_price_provider] = lambda: fake
    _choose_store(client)
    recipe_id = _recipe_id(seeded_db, "classic-chicken-fettuccine-alfredo")
    body = client.get(f"/api/v1/recipes/{recipe_id}/cost").json()

    for line in body["lines"]:
        assert line["status"] == "no_match"
        assert line["product"] is None
        assert line["used_cost"] is None
    assert body["recipe_cost"] == 0
    assert body["unpriced_count"] == 7  # nine lines minus two pantry staples


def test_excluded_and_unmeasured_lines(client, provider, seeded_db):
    _choose_store(client)
    curry_id = _recipe_id(seeded_db, "chickpea-spinach-curry")
    lines = _lines_by_name(client.get(f"/api/v1/recipes/{curry_id}/cost").json())
    assert lines["Fresh cilantro"]["status"] == "unmeasured"

    rice_id = _recipe_id(seeded_db, "vegetable-egg-fried-rice")
    lines = _lines_by_name(client.get(f"/api/v1/recipes/{rice_id}/cost").json())
    assert lines["White rice, cooked"]["status"] == "not_purchased"
    assert "cooked rice" in lines["White rice, cooked"]["reason"]


def test_provider_errors_return_502(client, seeded_db):
    working = FakeProvider()
    client.app.dependency_overrides[get_price_provider] = lambda: working
    _choose_store(client)

    failing = FakeProvider(fail_with=KrogerError("Kroger's daily request limit was reached. Try again later.", 429))
    client.app.dependency_overrides[get_price_provider] = lambda: failing
    recipe_id = _recipe_id(seeded_db, "classic-chicken-fettuccine-alfredo")
    response = client.get(f"/api/v1/recipes/{recipe_id}/cost")
    assert response.status_code == 502
    assert "limit" in response.json()["detail"]
