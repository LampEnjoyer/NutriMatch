"""Store pricing: match ingredients to store products and cost a recipe (when possible)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import units
from app.models import Ingredient, IngredientProductMatch, ProductPrice, Recipe, Store
from app.pricing.kroger import ProductResult, StoreResult
from app.pricing.selection import Candidate, choose_cheapest, effective_price, matches_ingredient, package_cost
from app.pricing.sizes import parse_size

SEARCH_LIMIT = 20


class PriceProvider(Protocol):
    provider_name: str

    def search_locations(self, zip_code: str, limit: int = 10) -> list[StoreResult]: ...

    def get_location(self, location_id: str) -> StoreResult | None: ...

    def search_products(self, term: str, location_id: str, limit: int = 20) -> list[ProductResult]: ...


def as_utc(value: datetime) -> datetime:
    # SQLite hands back naive datetimes even for timezone-aware columns; they were stored as UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def upsert_store(db: Session, provider_name: str, result: StoreResult) -> Store:
    store = db.scalar(
        select(Store).where(Store.provider == provider_name, Store.location_id == result.location_id)
    )
    if store is None:
        store = Store(provider=provider_name, location_id=result.location_id)
        db.add(store)
    store.name = result.name
    store.chain = result.chain
    store.address_line = result.address_line
    store.city = result.city
    store.state = result.state
    store.zip_code = result.zip_code
    db.flush()
    return store


def _upsert_product(db: Session, store: Store, result: ProductResult, now: datetime) -> ProductPrice:
    product = db.scalar(
        select(ProductPrice).where(
            ProductPrice.store_id == store.id, ProductPrice.provider_product_id == result.product_id
        )
    )
    if product is None:
        product = ProductPrice(store_id=store.id, provider_product_id=result.product_id)
        db.add(product)

    size = parse_size(result.size_text)
    product.description = result.description[:300]
    product.brand = result.brand
    product.size_text = result.size_text
    if size is None:
        product.package_quantity = None
        product.package_unit = None
    else:
        product.package_quantity = size.quantity
        product.package_unit = size.unit
    product.sold_by = result.sold_by
    product.regular_price = result.regular_price
    product.promo_price = result.promo_price
    product.product_url = result.product_url
    product.image_url = result.image_url
    product.fetched_at = now
    return product


def find_product(
    db: Session,
    provider: PriceProvider,
    ingredient: Ingredient,
    store: Store,
    now: datetime,
    cache_hours: int,
) -> IngredientProductMatch:
    match = db.scalar(
        select(IngredientProductMatch).where(
            IngredientProductMatch.ingredient_id == ingredient.id,
            IngredientProductMatch.store_id == store.id,
        )
    )

    if match is not None:
        if match.selected_by == "user":
            return match
        if now - as_utc(match.searched_at) < timedelta(hours=cache_hours):
            return match

    term = ingredient.price_search_term
    if term is None or term.strip() == "":
        term = ingredient.normalized_name

    results = provider.search_products(term, store.location_id, SEARCH_LIMIT)

    candidates: list[Candidate] = []
    products_by_id: dict[str, ProductPrice] = {}
    for result in results:
        product = _upsert_product(db, store, result, now)
        products_by_id[result.product_id] = product
        if not matches_ingredient(result.description, ingredient.normalized_name, ingredient.price_match_rules):
            continue
        candidates.append(
            Candidate(
                product_id=result.product_id,
                description=result.description,
                package_quantity=product.package_quantity,
                package_unit=product.package_unit,
                regular_price=product.regular_price,
                promo_price=product.promo_price,
            )
        )
    db.flush()

    preferred_dimension = None
    if ingredient.default_unit is not None:
        preferred_dimension = units.dimension_of(ingredient.default_unit)
    chosen = choose_cheapest(candidates, preferred_dimension)

    if match is None:
        match = IngredientProductMatch(ingredient_id=ingredient.id, store_id=store.id)
        db.add(match)
    match.selected_by = "auto"
    match.search_term = term
    match.candidates_considered = len(candidates)
    match.searched_at = now
    if chosen is None:
        match.product_price_id = None
        match.product = None
    else:
        match.product = products_by_id[chosen.product_id]
    db.flush()
    return match


@dataclass
class LineCost:
    position: int
    ingredient_id: int
    name: str
    quantity: float | None
    unit: str | None
    status: str  # priced | not_purchased | unmeasured | no_match | needs_conversion
    reason: str | None = None
    is_pantry_staple: bool = False
    product: ProductPrice | None = None
    package_price: float | None = None
    needed_in_package_units: float | None = None
    used_cost: float | None = None
    packages: int | None = None  # set on the first line of each ingredient only
    shopping_cost: float | None = None  # set on the first line of each ingredient only
    sold_by_weight: bool = False


@dataclass
class RecipeCost:
    store: Store
    servings: int
    lines: list[LineCost] = field(default_factory=list)
    recipe_cost: float = 0.0
    cost_per_serving: float = 0.0
    shopping_total: float = 0.0
    pantry_staples_cost: float = 0.0
    unpriced_count: int = 0
    oldest_price_at: datetime | None = None

    @property
    def is_complete(self) -> bool:
        return self.unpriced_count == 0


def cost_recipe(
    db: Session,
    provider: PriceProvider,
    recipe: Recipe,
    servings: int,
    store: Store,
    now: datetime,
    cache_hours: int,
) -> RecipeCost:
    if servings <= 0:
        raise ValueError("servings must be positive")

    factor = servings / recipe.servings
    result = RecipeCost(store=store, servings=servings)

    # Same ingredient on several lines (e.g. "oil, divided" written twice) buys packages once.
    first_line_for_ingredient: dict[int, LineCost] = {}
    total_needed_for_ingredient: dict[int, float] = {}
    matches: dict[int, IngredientProductMatch] = {}

    for line in recipe.ingredients:
        ingredient = line.ingredient
        scaled = None
        if line.quantity is not None:
            scaled = line.quantity * factor

        cost = LineCost(
            position=line.position,
            ingredient_id=ingredient.id,
            name=ingredient.name,
            quantity=scaled,
            unit=line.unit,
            status="priced",
            is_pantry_staple=ingredient.is_pantry_staple,
        )
        result.lines.append(cost)

        if ingredient.pricing_excluded_reason is not None:
            cost.status = "not_purchased"
            cost.reason = ingredient.pricing_excluded_reason
            continue
        if scaled is None or line.unit is None:
            cost.status = "unmeasured"
            cost.reason = "No amount listed, so it isn't priced."
            continue

        if ingredient.id not in matches:
            matches[ingredient.id] = find_product(db, provider, ingredient, store, now, cache_hours)
        match = matches[ingredient.id]
        product = match.product

        if product is None:
            cost.status = "no_match"
            cost.reason = f"No matching product with a price and size found at this store for “{match.search_term}”."
            continue

        cost.product = product
        cost.package_price = effective_price(product.regular_price, product.promo_price)
        if product.sold_by is not None and product.sold_by.lower() == "weight":
            cost.sold_by_weight = True

        needed = units.convert(
            scaled,
            line.unit,
            product.package_unit,
            density_g_per_ml=ingredient.density_g_per_ml,
            grams_per_count=ingredient.grams_per_count,
        )
        if needed is None:
            cost.status = "needs_conversion"
            cost.reason = (
                f"The recipe measures this in {line.unit} and the product is sold by {product.package_unit}; "
                f"converting needs ingredient data that isn't loaded yet."
            )
            continue

        cost.needed_in_package_units = needed
        per_line = package_cost(needed, product.package_quantity, cost.package_price)
        cost.used_cost = per_line.used_cost

        if ingredient.id not in first_line_for_ingredient:
            first_line_for_ingredient[ingredient.id] = cost
            total_needed_for_ingredient[ingredient.id] = needed
        else:
            total_needed_for_ingredient[ingredient.id] += needed

        fetched = as_utc(product.fetched_at)
        if result.oldest_price_at is None or fetched < result.oldest_price_at:
            result.oldest_price_at = fetched

    for ingredient_id, first in first_line_for_ingredient.items():
        combined = package_cost(
            total_needed_for_ingredient[ingredient_id], first.product.package_quantity, first.package_price
        )
        first.packages = combined.packages
        first.shopping_cost = combined.shopping_cost

    for cost in result.lines:
        if cost.status in ("no_match", "needs_conversion") and not cost.is_pantry_staple:
            result.unpriced_count += 1
        if cost.status != "priced":
            continue
        if cost.is_pantry_staple:
            if cost.shopping_cost is not None:
                result.pantry_staples_cost += cost.shopping_cost
            continue
        result.recipe_cost += cost.used_cost
        if cost.shopping_cost is not None:
            result.shopping_total += cost.shopping_cost

    result.cost_per_serving = result.recipe_cost / servings
    return result
