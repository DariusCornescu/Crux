from functools import lru_cache

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

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    fcm_service_account_json_path: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
