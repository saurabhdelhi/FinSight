"""
FinSight application configuration.
Uses pydantic-settings for environment-based config with .env file support.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "FinSight"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://finsight:finsight_pass@localhost:5432/finsight_db"
    )

    # ── JWT Auth ─────────────────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Tally Defaults ───────────────────────────────────────────────────
    tally_default_host: str = "localhost"
    tally_default_port: int = 9000
    tally_request_timeout: int = 30  # seconds

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # ── Report Storage ───────────────────────────────────────────────────
    report_storage_path: str = "./reports"

    @property
    def report_dir(self) -> Path:
        """Resolved report storage directory, created on first access."""
        path = Path(self.report_storage_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton instance
settings = Settings()
