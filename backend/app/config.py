from functools import lru_cache

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
    # Must start with "postgresql" and include ?sslmode=require for Neon.
    database_url: str

    # ── JWT ─────────────────────────────────────────────────────────────────
    # Minimum 32 characters; used as the HS256 signing secret.
    jwt_secret: str
    jwt_expire_hours: int = 24

    # ── CORS ────────────────────────────────────────────────────────────────
    # Stored as a plain string; use cors_origins_list for the parsed list.
    # Example: "http://localhost:5173,https://your-app.vercel.app"
    cors_origins: str = "http://localhost:5173"

    # ── App ──────────────────────────────────────────────────────────────────
    environment: str = "development"

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


# Module-level singleton — imported everywhere that needs settings.
# Uses lru_cache so the .env file is read exactly once per process,
# and tests can call get_settings.cache_clear() to reload with different env vars.


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
