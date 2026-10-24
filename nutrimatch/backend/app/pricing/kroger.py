"""Minimal client for the Kroger Public API (client-credentials flow, public data only).

Endpoints and limits used here (checked against a maintained client library, Oct 2026):
- POST /v1/connect/oauth2/token   HTTP Basic client_id:client_secret, grant_type=client_credentials
- GET  /v1/locations              filter.zipCode.near (5 digits), filter.limit (1-200)
- GET  /v1/locations/{locationId}
- GET  /v1/products               filter.term (3+ chars, max 8 words), filter.locationId, filter.limit (1-50)

Prices are only returned when filter.locationId is set. Kroger reports promo = 0 for "no sale".
"""

import base64
import time
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx

KROGER_WEB = "https://www.kroger.com"
SCOPE = "product.compact"
TIMEOUT_SECONDS = 10.0


class KrogerError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class StoreResult:
    location_id: str
    name: str
    chain: str | None
    address_line: str | None
    city: str | None
    state: str | None
    zip_code: str | None


@dataclass(frozen=True)
class ProductResult:
    product_id: str
    description: str
    brand: str | None
    size_text: str | None
    sold_by: str | None
    regular_price: float | None
    promo_price: float | None
    product_url: str
    image_url: str | None


def _parse_store(raw: dict) -> StoreResult:
    address = raw.get("address") or {}
    return StoreResult(
        location_id=str(raw.get("locationId", "")),
        name=raw.get("name") or "Kroger store",
        chain=raw.get("chain"),
        address_line=address.get("addressLine1"),
        city=address.get("city"),
        state=address.get("state"),
        zip_code=address.get("zipCode"),
    )


def _featured_image(raw: dict) -> str | None:
    images = raw.get("images") or []
    chosen = None
    for image in images:
        if image.get("featured"):
            chosen = image
            break
    if chosen is None and len(images) > 0:
        chosen = images[0]
    if chosen is None:
        return None
    for size in chosen.get("sizes") or []:
        if size.get("size") == "medium":
            return size.get("url")
    return None


def _product_url(raw: dict, description: str) -> str:
    # Not every response version is known to include a product page path; fall back to a search link.
    page = raw.get("productPageURI")
    if isinstance(page, str) and page != "":
        if page.startswith("/"):
            return KROGER_WEB + page
        return page
    return f"{KROGER_WEB}/search?query={quote_plus(description)}"


def _to_price(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    if value <= 0:
        return None
    return float(value)


def parse_products(payload: dict) -> list[ProductResult]:
    results: list[ProductResult] = []
    for raw in payload.get("data") or []:
        product_id = raw.get("productId")
        description = raw.get("description")
        if not product_id or not description:
            continue
        items = raw.get("items") or []
        if len(items) == 0:
            continue
        # A product normally has one item at a given store; use the first.
        item = items[0]
        price = item.get("price") or {}
        results.append(
            ProductResult(
                product_id=str(product_id),
                description=description.strip(),
                brand=raw.get("brand"),
                size_text=item.get("size"),
                sold_by=item.get("soldBy"),
                regular_price=_to_price(price.get("regular")),
                promo_price=_to_price(price.get("promo")),
                product_url=_product_url(raw, description.strip()),
                image_url=_featured_image(raw),
            )
        )
    return results


class KrogerClient:
    provider_name = "kroger"

    def __init__(self, client_id: str, client_secret: str, base_url: str, http: httpx.Client | None = None):
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._http = http if http is not None else httpx.Client(timeout=TIMEOUT_SECONDS)
        self._token: str | None = None
        self._token_expires_at = 0.0

    def _fetch_token(self) -> None:
        credentials = f"{self._client_id}:{self._client_secret}".encode()
        headers = {
            "Authorization": "Basic " + base64.b64encode(credentials).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            response = self._http.post(
                f"{self._base_url}/v1/connect/oauth2/token",
                headers=headers,
                data={"grant_type": "client_credentials", "scope": SCOPE},
            )
        except httpx.HTTPError as exc:
            raise KrogerError("Couldn't reach Kroger to sign in.") from exc

        if response.status_code == 401:
            raise KrogerError("Kroger rejected the client ID or secret. Check KROGER_CLIENT_ID and KROGER_CLIENT_SECRET.", 401)
        if response.status_code != 200:
            raise KrogerError(f"Kroger sign-in failed with status {response.status_code}.", response.status_code)

        body = response.json()
        self._token = body["access_token"]
        expires_in = float(body.get("expires_in", 1800))
        # Renew a minute early so a request never goes out with a token about to expire.
        self._token_expires_at = time.monotonic() + expires_in - 60

    def _get(self, path: str, params: dict) -> dict:
        retried = False
        while True:
            if self._token is None or time.monotonic() >= self._token_expires_at:
                self._fetch_token()

            try:
                response = self._http.get(
                    f"{self._base_url}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
                )
            except httpx.HTTPError as exc:
                raise KrogerError("Couldn't reach Kroger.") from exc

            if response.status_code == 401 and not retried:
                # Token revoked or expired early: get a new one and try once more.
                self._token = None
                retried = True
                continue
            if response.status_code == 429:
                raise KrogerError("Kroger's daily request limit was reached. Try again later.", 429)
            if response.status_code != 200:
                raise KrogerError(f"Kroger request failed with status {response.status_code}.", response.status_code)
            return response.json()

    def search_locations(self, zip_code: str, limit: int = 10) -> list[StoreResult]:
        payload = self._get("/v1/locations", {"filter.zipCode.near": zip_code, "filter.limit": limit})
        stores = []
        for raw in payload.get("data") or []:
            if raw.get("locationId"):
                stores.append(_parse_store(raw))
        return stores

    def get_location(self, location_id: str) -> StoreResult | None:
        try:
            payload = self._get(f"/v1/locations/{location_id}", {})
        except KrogerError as exc:
            if exc.status_code == 404:
                return None
            raise
        raw = payload.get("data")
        if not raw or not raw.get("locationId"):
            return None
        return _parse_store(raw)

    def search_products(self, term: str, location_id: str, limit: int = 20) -> list[ProductResult]:
        params = {"filter.term": term, "filter.locationId": location_id, "filter.limit": limit}
        return parse_products(self._get("/v1/products", params))
