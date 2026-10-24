"""Recipes ranked for the current user's saved preferences."""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.recommend import recommend
from app.schemas import RecommendationList

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationList)
def get_recommendations(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> RecommendationList:
    return recommend(db, user.preferences, limit, offset)
