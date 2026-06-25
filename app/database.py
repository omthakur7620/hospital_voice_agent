"""
Centralized application configuration.

All environment-dependent values live here. Nothing else in the codebase
should call os.getenv() directly — import `settings` from this module instead.
This keeps config testable and makes it obvious what env vars the app needs.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App identity ---
    APP_NAME: str = "Hospital Voice AI Receptionist Backend"
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = False

    # --- Database ---
    # Async driver required: postgresql+asyncpg://user:pass@host:port/dbname
    DATABASE_URL: str

    # --- CORS ---
    # Comma-separated in .env, e.g. "https://vapi.ai,https://yourdomain.com"
    ALLOWED_ORIGINS: str = "*"

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    # --- Timezone ---
    TIMEZONE: str = "Asia/Kolkata"  # Hospital is in Pune, India

    # --- Business rules (kept here, not hardcoded in services) ---
    SLOT_DURATION_MINUTES: int = 30   # used to compute alternative slots
    MAX_ALTERNATIVE_SLOTS: int = 3
    BOOKING_WINDOW_DAYS: int = 30     # how far ahead patients can book

    # --- Seed data path ---
    HOSPITAL_DATA_PATH: str = "data/hospital_data.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def database_url_async(self) -> str:
        """
        Ensures the database URL uses the asyncpg driver.
        Converts postgresql:// to postgresql+asyncpg:// if needed.
        """
        url = self.DATABASE_URL
        # If already has +asyncpg, return as is
        if "+asyncpg" in url:
            return url
        # Replace postgresql:// with postgresql+asyncpg://
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # If it starts with postgresql+ (but not asyncpg), add asyncpg
        if url.startswith("postgresql+"):
            return url.replace("postgresql+", "postgresql+asyncpg+", 1)
        # Fallback: just return as is
        return url


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance. lru_cache ensures the .env file is parsed once,
    not on every import — important since config is imported widely.
    """
    return Settings()


# Convenience singleton for direct import: `from app.config import settings`
settings = get_settings()