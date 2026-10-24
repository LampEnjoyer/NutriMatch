from fastapi import APIRouter

from app.api.v1 import health, preferences, recipes

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(recipes.router)
router.include_router(preferences.router)
