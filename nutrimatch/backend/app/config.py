from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./nutrimatch.db"

    # Comma-separated list of allowed frontend origins.
    cors_origins: str = "http://localhost:5173"

    # Until real auth exists, every request acts as this seeded user.
    demo_user_email: str = "demo@nutrimatch.local"

    # USDA FoodData Central (https://fdc.nal.usda.gov/api-guide). Optional; used from Phase 3.
    usda_fdc_api_key: str | None = None

    def cors_origin_list(self) -> list[str]:
        origins = []
        for raw in self.cors_origins.split(","):
            origin = raw.strip()
            if origin != "":
                origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
