"""Centralized configuration management for LifePilot."""
import os
from pathlib import Path
from typing import Optional
from functools import lru_cache

from dotenv import load_dotenv

# Load environment variables once at module import
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # === API Keys ===
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        
        # === Database ===
        self.database_path: str = os.getenv("DATABASE_PATH", "./database/lifepilot.db")
        
        # === Application ===
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        
        # === AI Models ===
        self.ai_model_fast: str = os.getenv("AI_MODEL_FAST", "llama-3.1-8b-instant")
        self.ai_model_smart: str = os.getenv("AI_MODEL_SMART", "llama-3.3-70b-versatile")
        self.ai_temperature: float = float(os.getenv("AI_TEMPERATURE", "0.3"))
        self.ai_max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "1024"))
        self.ai_timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
        
        # === API Settings ===
        self.cors_origins: list = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        self.api_version: str = "v1"
        
        # === Rate Limiting ===
        self.rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    
    def get_db_path(self) -> str:
        """Get the absolute path to the database file."""
        return str(Path(self.database_path).resolve())
    
    def validate(self) -> list:
        """
        Validate required settings. Returns list of validation errors.
        Call this on application startup.
        """
        errors = []
        
        if not self.groq_api_key:
            errors.append("GROQ_API_KEY environment variable is not set")
        
        return errors
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance. 
    Use this function to access settings throughout the application.
    """
    return Settings()


# Convenience function for quick access
settings = get_settings()
