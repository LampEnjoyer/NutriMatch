from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

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
