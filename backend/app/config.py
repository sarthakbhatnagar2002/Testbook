from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    session_secret: str = ""
    frontend_origin: str = "http://localhost:5173"
    environment: str = "development"
    upload_dir: str = "./uploads"
    # "lax" works when frontend and backend share a site (e.g. local dev).
    # Set to "none" when they're on different origins (e.g. two separate
    # Render services) or the browser will silently drop the session cookie.
    cookie_samesite: str = "lax"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if len(settings.session_secret) < 32:
        raise RuntimeError("SESSION_SECRET must be set and at least 32 characters long")
    return settings
