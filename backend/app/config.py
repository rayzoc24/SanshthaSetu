from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    All secrets must be supplied via the environment — never hard-coded.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str

    # ── JWT ─────────────────────────────────────────────────────────────────
    jwt_secret: str
    jwt_expire_hours: int = 24

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173"

    # ── App ──────────────────────────────────────────────────────────────────
    environment: str = "development"

    # ── Storage (S3-compatible: Neon Object Storage / Cloudflare R2) ────────
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_endpoint_url_s3: Optional[str] = None
    aws_region: str = "ap-southeast-1"
    neon_storage_bucket: str = "assets"

    # ── Gemini AI ───────────────────────────────────────────────────────────
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"

    # ── Derived properties ───────────────────────────────────────────────────

    @property
    def cors_origins_list(self) -> list[str]:
        """Split CORS_ORIGINS on commas, strip whitespace from each entry."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_required(self) -> None:
        """
        Raise ValueError for any setting that cannot be validated by type alone.
        Called once at startup in create_app().
        """
        if not self.database_url.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql' (got: "
                f"{self.database_url[:30]!r})"
            )
        if len(self.jwt_secret) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters (got {len(self.jwt_secret)})"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
