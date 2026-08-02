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
