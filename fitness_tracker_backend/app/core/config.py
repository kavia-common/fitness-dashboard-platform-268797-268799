from __future__ import annotations

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL", description="Async SQLAlchemy database URL.")
    jwt_secret: str = Field(..., alias="JWT_SECRET", description="JWT signing secret.")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM", description="JWT signing algorithm.")
    access_token_expire_minutes: int = Field(
        60 * 24 * 7,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
        description="Access token expiration in minutes.",
    )
    cors_origins: str = Field(
        "*",
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins (or * for dev).",
    )
    log_level: str = Field("INFO", alias="LOG_LEVEL", description="Logging level.")

    def cors_origin_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a list."""
        raw = (self.cors_origins or "").strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
