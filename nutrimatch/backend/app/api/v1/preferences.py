"""Read and replace the current user's preferences, and describe the form questions."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.models import UserPreferences
from app.preference_options import build_options
from app.schemas import PreferenceOptions, PreferencesIn, PreferencesOut

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/options", response_model=PreferenceOptions)
def get_preference_options() -> PreferenceOptions:
    return build_options()


@router.get("", response_model=PreferencesOut)
def get_preferences(user: CurrentUser, db: DbSession) -> UserPreferences:
    if user.preferences is None:
        user.preferences = UserPreferences()
        db.commit()
        db.refresh(user.preferences)
    return user.preferences


@router.put("", response_model=PreferencesOut)
def replace_preferences(body: PreferencesIn, user: CurrentUser, db: DbSession) -> UserPreferences:
    preferences = user.preferences
    if preferences is None:
        preferences = UserPreferences()
        user.preferences = preferences

    preferences.nutrient_levels = dict(body.nutrient_levels)
    preferences.time_preference = body.time_preference
    preferences.meal_types = list(body.meal_types)
    preferences.meal_size = body.meal_size
    preferences.allergies = list(body.allergies)
    db.commit()
    db.refresh(preferences)
    return preferences
