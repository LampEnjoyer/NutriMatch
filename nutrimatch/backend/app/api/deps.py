from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.pricing.kroger import KrogerClient
from app.pricing.service import PriceProvider

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession) -> User:
    """Placeholder auth: every request acts as the seeded demo user.

    Endpoints that touch user-owned records depend on this, so swapping in real auth later
    only changes this function.
    """
    email = get_settings().demo_user_email
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo user not found. Run the seed script: python -m app.seed.seed",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


_kroger_client: KrogerClient | None = None


def get_price_provider() -> PriceProvider | None:
    """The configured store-price provider, or None when no Kroger credentials are set.

    One client is reused across requests so its access token is reused until it expires.
    """
    global _kroger_client
    settings = get_settings()
    if not settings.kroger_configured():
        return None
    if _kroger_client is None:
        _kroger_client = KrogerClient(
            settings.kroger_client_id, settings.kroger_client_secret, settings.kroger_api_base_url
        )
    return _kroger_client


OptionalPriceProvider = Annotated[PriceProvider | None, Depends(get_price_provider)]


def require_price_provider(provider: OptionalPriceProvider) -> PriceProvider:
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Store prices aren't set up. Add KROGER_CLIENT_ID and KROGER_CLIENT_SECRET to backend/.env.",
        )
    return provider


PriceProviderDep = Annotated[PriceProvider, Depends(require_price_provider)]
