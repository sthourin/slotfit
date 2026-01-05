"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
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
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
