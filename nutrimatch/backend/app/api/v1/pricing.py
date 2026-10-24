"""Store pricing endpoints (Kroger).

- GET  /pricing/status            whether prices are configured, and the user's store
- GET  /stores?zip_code=12345     nearby stores from the provider (not saved)
- PUT  /preferences/store         save the user's store
- GET  /recipes/{id}/cost         per-ingredient prices and totals at the user's store
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, OptionalPriceProvider, PriceProviderDep
from app.config import get_settings
from app.models import Recipe, RecipeIngredient, Store
from app.pricing.service import LineCost, RecipeCost, cost_recipe, upsert_store
from app.schemas import (
    ErrorResponse,
    LineCostOut,
    PricingStatus,
    ProductOut,
    RecipeCostOut,
    SetStoreRequest,
    StoreOut,
)

router = APIRouter(tags=["pricing"])


def _money(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def _store_out(store: Store) -> StoreOut:
    return StoreOut(
        provider=store.provider,
        location_id=store.location_id,
        name=store.name,
        chain=store.chain,
        address_line=store.address_line,
        city=store.city,
        state=store.state,
        zip_code=store.zip_code,
    )


def _line_out(line: LineCost) -> LineCostOut:
    product_out = None
    if line.product is not None and line.package_price is not None:
        product = line.product
        on_sale = product.promo_price is not None and line.package_price == product.promo_price
        product_out = ProductOut(
            description=product.description,
            brand=product.brand,
            size_text=product.size_text,
            package_price=_money(line.package_price),
            regular_price=_money(product.regular_price),
            promo_price=_money(product.promo_price),
            on_sale=on_sale,
            sold_by_weight=line.sold_by_weight,
            product_url=product.product_url,
            image_url=product.image_url,
            fetched_at=product.fetched_at,
        )

    return LineCostOut(
        position=line.position,
        ingredient_id=line.ingredient_id,
        name=line.name,
        quantity=line.quantity,
        unit=line.unit,
        status=line.status,
        reason=line.reason,
        is_pantry_staple=line.is_pantry_staple,
        product=product_out,
        used_cost=_money(line.used_cost),
        packages=line.packages,
        shopping_cost=_money(line.shopping_cost),
    )


def _cost_out(recipe_id: int, cost: RecipeCost) -> RecipeCostOut:
    lines = []
    for line in cost.lines:
        lines.append(_line_out(line))
    return RecipeCostOut(
        recipe_id=recipe_id,
        servings=cost.servings,
        store=_store_out(cost.store),
        recipe_cost=_money(cost.recipe_cost),
        cost_per_serving=_money(cost.cost_per_serving),
        shopping_total=_money(cost.shopping_total),
        pantry_staples_cost=_money(cost.pantry_staples_cost),
        unpriced_count=cost.unpriced_count,
        is_complete=cost.is_complete,
        oldest_price_at=cost.oldest_price_at,
        lines=lines,
    )


@router.get("/pricing/status", response_model=PricingStatus)
def pricing_status(user: CurrentUser, provider: OptionalPriceProvider) -> PricingStatus:
    store_out = None
    if user.preferences is not None and user.preferences.preferred_store is not None:
        store_out = _store_out(user.preferences.preferred_store)
    return PricingStatus(configured=provider is not None, provider="kroger", store=store_out)


@router.get(
    "/stores",
    response_model=list[StoreOut],
    responses={502: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def search_stores(
    provider: PriceProviderDep,
    zip_code: str = Query(pattern=r"^[0-9]{5}$", description="5-digit US ZIP code"),
) -> list[StoreOut]:
    stores = []
    for result in provider.search_locations(zip_code, limit=10):
        stores.append(
            StoreOut(
                provider=provider.provider_name,
                location_id=result.location_id,
                name=result.name,
                chain=result.chain,
                address_line=result.address_line,
                city=result.city,
                state=result.state,
                zip_code=result.zip_code,
            )
        )
    return stores


@router.put(
    "/preferences/store",
    response_model=StoreOut,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def set_store(body: SetStoreRequest, user: CurrentUser, db: DbSession, provider: PriceProviderDep) -> StoreOut:
    result = provider.get_location(body.location_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Store {body.location_id} not found")

    store = upsert_store(db, provider.provider_name, result)
    # get_current_user received this same session (FastAPI caches get_db per request).
    user.preferences.preferred_store_id = store.id
    db.commit()
    return _store_out(store)


@router.get(
    "/recipes/{recipe_id}/cost",
    response_model=RecipeCostOut,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def recipe_cost(
    recipe_id: int,
    user: CurrentUser,
    db: DbSession,
    provider: PriceProviderDep,
    servings: int | None = Query(default=None, ge=1, le=100),
) -> RecipeCostOut:
    store_id = None
    if user.preferences is not None:
        store_id = user.preferences.preferred_store_id
    if store_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Choose a store to see prices.")

    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
    )
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recipe {recipe_id} not found")

    store = db.get(Store, store_id)
    if servings is None:
        servings = recipe.servings

    cost = cost_recipe(
        db, provider, recipe, servings, store, now=datetime.now(UTC), cache_hours=get_settings().price_cache_hours
    )
    # Persist looked-up products and matches so the next request reuses them.
    db.commit()
    return _cost_out(recipe.id, cost)
