from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    session_secret: str = ""
    teacher_invite_code: str | None = "teacher123"
    frontend_origin: str = "http://localhost:5173"
    environment: str = "development"
    upload_dir: str = "./uploads"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if len(settings.session_secret) < 32:
        raise RuntimeError("SESSION_SECRET must be set and at least 32 characters long")
    return settings
