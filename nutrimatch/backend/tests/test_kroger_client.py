"""KrogerClient against a mocked HTTP transport. Payloads follow the shape of real API responses."""

import base64
from urllib.parse import parse_qs

import httpx
import pytest

from app.pricing.kroger import KrogerClient, KrogerError, parse_products

BASE = "https://api.kroger.com"


def _product(product_id, description, size, regular, promo=0, sold_by="Unit", page=None):
    raw = {
        "productId": product_id,
        "upc": product_id,
        "brand": "Kroger",
        "description": description,
        "images": [
            {
                "perspective": "front",
                "featured": True,
                "sizes": [{"size": "medium", "url": f"https://www.kroger.com/product/images/medium/front/{product_id}"}],
            }
        ],
        "items": [{"itemId": product_id, "size": size, "soldBy": sold_by, "price": {"regular": regular, "promo": promo}}],
    }
    if page is not None:
        raw["productPageURI"] = page
    return raw


class Recorder:
    def __init__(self, routes):
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        handler = self.routes[request.url.path]
        return handler(request)


def _token_ok(_request):
    return httpx.Response(200, json={"access_token": "tok-1", "expires_in": 1800, "token_type": "bearer"})


def _client(routes):
    recorder = Recorder(routes)
    http = httpx.Client(transport=httpx.MockTransport(recorder))
    return KrogerClient("my-id", "my-secret", BASE, http=http), recorder


def test_token_request_uses_basic_auth_and_client_credentials():
    client, recorder = _client(
        {"/v1/connect/oauth2/token": _token_ok, "/v1/products": lambda r: httpx.Response(200, json={"data": []})}
    )
    client.search_products("milk", "01400513")

    token_request = recorder.requests[0]
    expected = "Basic " + base64.b64encode(b"my-id:my-secret").decode()
    assert token_request.headers["Authorization"] == expected
    form = parse_qs(token_request.content.decode())
    assert form == {"grant_type": ["client_credentials"], "scope": ["product.compact"]}


def test_product_search_sends_filters_and_bearer_token():
    client, recorder = _client(
        {"/v1/connect/oauth2/token": _token_ok, "/v1/products": lambda r: httpx.Response(200, json={"data": []})}
    )
    client.search_products("2% milk", "01400513", limit=20)

    search = recorder.requests[1]
    assert search.headers["Authorization"] == "Bearer tok-1"
    assert search.url.params["filter.term"] == "2% milk"
    assert search.url.params["filter.locationId"] == "01400513"
    assert search.url.params["filter.limit"] == "20"


def test_token_is_reused_until_it_expires():
    client, recorder = _client(
        {"/v1/connect/oauth2/token": _token_ok, "/v1/products": lambda r: httpx.Response(200, json={"data": []})}
    )
    client.search_products("milk", "01400513")
    client.search_products("eggs", "01400513")
    token_calls = [r for r in recorder.requests if r.url.path == "/v1/connect/oauth2/token"]
    assert len(token_calls) == 1


def test_retries_once_with_a_new_token_after_401():
    responses = iter([httpx.Response(401), httpx.Response(200, json={"data": []})])
    client, recorder = _client({"/v1/connect/oauth2/token": _token_ok, "/v1/products": lambda r: next(responses)})
    assert client.search_products("milk", "01400513") == []
    token_calls = [r for r in recorder.requests if r.url.path == "/v1/connect/oauth2/token"]
    assert len(token_calls) == 2


def test_bad_credentials_raise_a_clear_error():
    client, _ = _client({"/v1/connect/oauth2/token": lambda r: httpx.Response(401)})
    with pytest.raises(KrogerError) as exc_info:
        client.search_products("milk", "01400513")
    assert "KROGER_CLIENT_ID" in exc_info.value.message


def test_rate_limit_raises():
    client, _ = _client({"/v1/connect/oauth2/token": _token_ok, "/v1/products": lambda r: httpx.Response(429)})
    with pytest.raises(KrogerError) as exc_info:
        client.search_products("milk", "01400513")
    assert exc_info.value.status_code == 429


def test_network_failure_raises_kroger_error():
    def boom(_request):
        raise httpx.ConnectError("no route")

    client, _ = _client({"/v1/connect/oauth2/token": boom})
    with pytest.raises(KrogerError):
        client.search_products("milk", "01400513")


def test_parse_products_reads_prices_sizes_and_links():
    payload = {
        "data": [
            _product("0001111041600", "Kroger® 2% Reduced Fat Milk", "1/2 gal", 2.29, promo=0),
            _product("0001111050000", "Kroger® Unsalted Butter", "16 oz", 4.99, promo=3.99, page="/p/butter/0001111050000"),
            {"productId": "0000000000001", "description": "No items here", "items": []},
        ]
    }
    milk, butter = parse_products(payload)

    assert milk.size_text == "1/2 gal"
    assert milk.regular_price == 2.29
    assert milk.promo_price is None  # Kroger's 0 means no sale
    assert milk.product_url.startswith("https://www.kroger.com/search?query=")
    assert milk.image_url.endswith("/0001111041600")

    assert butter.promo_price == 3.99
    assert butter.product_url == "https://www.kroger.com/p/butter/0001111050000"


def test_locations_parse_address():
    def locations(_request):
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "locationId": "01400513",
                        "chain": "KROGER",
                        "name": "Kroger - Hilliard",
                        "address": {"addressLine1": "1 Main St", "city": "Hilliard", "state": "OH", "zipCode": "43026"},
                    }
                ]
            },
        )

    client, recorder = _client({"/v1/connect/oauth2/token": _token_ok, "/v1/locations": locations})
    stores = client.search_locations("43026")
    assert recorder.requests[1].url.params["filter.zipCode.near"] == "43026"
    assert stores[0].location_id == "01400513"
    assert stores[0].city == "Hilliard"
