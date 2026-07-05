from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://splitrail:splitrail@localhost:5432/splitrail"
    redis_url: str = "redis://localhost:6379/0"

    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/integrations/strava/callback"

    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/integrations/spotify/callback"

    llm_provider: str = "openrouter"  # "openrouter" | "anthropic"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.6"

    fcm_service_account_json_path: str = ""

    @field_validator("database_url")
    @classmethod
    def _normalize_db_scheme(cls, v: str) -> str:
        """DO App Platform / Heroku-style URLs use postgres:// or postgresql://;
        SQLAlchemy needs the psycopg3 driver spelled out."""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
