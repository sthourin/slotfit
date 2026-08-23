"""
Application configuration
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

# Repo root, resolved from this file rather than the working directory.
# config.py -> core -> app -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]

# The canonical env file for the whole repo. An absolute path is deliberate:
# a CWD-relative env_file silently loads nothing when a command is run from
# anywhere but backend/, leaving every setting on its hardcoded default.
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/slotfit"

    # AI Service
    AI_PROVIDER: str = "claude"  # claude or ollama
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    # Configurable so a retired model is an env change, not a code change. The
    # previous value was hardcoded as `claude-3-sonnet-20240229`, which Anthropic
    # retired on 2025-07-21 - every recommendation request 404'd for months and
    # fell through to the rule-based provider without anything surfacing it.
    # Model IDs carry no date suffix.
    AI_MODEL: str = "claude-opus-5"
    # A recommendation payload is a JSON object with up to 15 entries. 2000 was
    # the old value and truncates mid-object, which reads as a parse failure.
    AI_MAX_TOKENS: int = 16000

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # CORS (comma-separated string, will be split)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Integrations
    # Hevy workout export (hevy/pull_hevy.py). Optional; the app does not use it.
    HEVY_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
