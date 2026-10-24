from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.api.deps import DbSession
from app.models import Recipe

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: DbSession) -> dict:
    db.execute(text("SELECT 1"))
    recipe_count = db.scalar(select(func.count()).select_from(Recipe))
    return {"status": "ok", "database": "ok", "recipes": recipe_count}
