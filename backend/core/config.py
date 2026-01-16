"""Centralized configuration management for LifePilot."""
import os
from pathlib import Path
from typing import Optional, Dict, List
from functools import lru_cache
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from project root (parent of backend/)
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback to current directory


@dataclass
class ModelConfig:
    """Configuration for a specific AI model."""
    name: str
    context_window: int
    tokens_per_minute: int
    best_for: List[str]
    
    
class ModelRegistry:
    """
    Registry of Groq models with task-specific assignments (Updated January 2026).
    
    Task Categories:
    1. CATEGORIZATION - Item categorization, type detection (fast, simple)
    2. ANALYSIS - Bookmark analysis, pattern detection (smart, detailed)
    3. CONVERSATION - Agent chat, responses (balanced, conversational)
    4. PLANNING - Decision analysis, weekly review (smart, reasoning)
    5. TRANSCRIPTION - Voice to text (Whisper model)
    
    Reserve models are used as fallbacks when primary models fail.
    
    Free Tier Limits (2026):
    - 30 RPM (requests per minute)
    - 14,400 RPD (requests per day)
    - 40,000 TPM (tokens per minute) varies by model
    """
    
    # === PRIMARY MODELS (5 task-specific) - Updated for 2026 ===
    
    # Fast model for quick categorization tasks
    # Llama 3.1 8B - High throughput, simple classification, 30K TPM
    MODEL_CATEGORIZATION = "llama-3.1-8b-instant"
    
    # Smart model for detailed analysis
    # DeepSeek R1 Distill - Excellent reasoning for bookmark/pattern analysis
    MODEL_ANALYSIS = "deepseek-r1-distill-llama-70b"
    
    # Balanced model for conversational AI
    # Llama 4 Scout - Latest Llama, great for natural chat
    MODEL_CONVERSATION = "llama-4-scout-17b-16e-instruct"
    
    # Reasoning model for planning tasks
    # Qwen3 32B - Strong reasoning for decisions/reviews
    MODEL_PLANNING = "qwen-qwq-32b"
    
    # Specialized model for voice transcription
    MODEL_WHISPER = "whisper-large-v3"
    
    # === RESERVE MODELS (3 fallbacks) - Updated for 2026 ===
    
    # First fallback - proven reliable, fast
    RESERVE_1 = "llama-3.3-70b-versatile"
    
    # Second fallback - smaller fast model
    RESERVE_2 = "llama-3.2-3b-preview"
    
    # Third fallback - lightweight but capable
    RESERVE_3 = "gemma2-9b-it"
    
    # Model metadata for intelligent selection (2026 specs)
    MODELS: Dict[str, ModelConfig] = {
        # === Primary Models ===
        "llama-3.1-8b-instant": ModelConfig(
            name="llama-3.1-8b-instant",
            context_window=8192,
            tokens_per_minute=30000,
            best_for=["categorization", "fast_classification", "simple_tasks"]
        ),
        "deepseek-r1-distill-llama-70b": ModelConfig(
            name="deepseek-r1-distill-llama-70b",
            context_window=131072,  # 128K context!
            tokens_per_minute=50000,
            best_for=["analysis", "complex_reasoning", "research", "deep_analysis"]
        ),
        "llama-4-scout-17b-16e-instruct": ModelConfig(
            name="llama-4-scout-17b-16e-instruct",
            context_window=32768,
            tokens_per_minute=40000,
            best_for=["conversation", "chat", "natural_responses", "instruction_following"]
        ),
        "qwen-qwq-32b": ModelConfig(
            name="qwen-qwq-32b",
            context_window=32768,
            tokens_per_minute=35000,
            best_for=["planning", "reasoning", "structured_output", "decisions"]
        ),
        "whisper-large-v3": ModelConfig(
            name="whisper-large-v3",
            context_window=0,  # Audio model - measured in seconds
            tokens_per_minute=0,
            best_for=["transcription", "speech_to_text"]
        ),
        # === Reserve/Fallback Models ===
        "llama-3.3-70b-versatile": ModelConfig(
            name="llama-3.3-70b-versatile",
            context_window=32768,
            tokens_per_minute=70000,
            best_for=["general", "analysis", "conversation", "fallback"]
        ),
        "llama-3.2-3b-preview": ModelConfig(
            name="llama-3.2-3b-preview",
            context_window=8192,
            tokens_per_minute=30000,
            best_for=["fast", "simple_tasks", "fallback"]
        ),
        "gemma2-9b-it": ModelConfig(
            name="gemma2-9b-it",
            context_window=8192,
            tokens_per_minute=15000,
            best_for=["general", "fallback", "instruction_following", "lightweight"]
        ),
    }
    
    @classmethod
    def get_model_for_task(cls, task_type: str) -> str:
        """Get the appropriate model for a task type."""
        task_models = {
            # Primary task types
            "categorization": cls.MODEL_CATEGORIZATION,
            "analysis": cls.MODEL_ANALYSIS,
            "conversation": cls.MODEL_CONVERSATION,
            "planning": cls.MODEL_PLANNING,
            "transcription": cls.MODEL_WHISPER,
            # Aliases for convenience
            "fast": cls.MODEL_CATEGORIZATION,
            "smart": cls.MODEL_ANALYSIS,
            "chat": cls.MODEL_CONVERSATION,
            "review": cls.MODEL_PLANNING,
            "voice": cls.MODEL_WHISPER,
            "reason": cls.MODEL_PLANNING,
            "deep": cls.MODEL_ANALYSIS,
        }
        return task_models.get(task_type, cls.MODEL_CATEGORIZATION)
    
    @classmethod
    def get_fallback_chain(cls, primary_model: str) -> List[str]:
        """Get ordered list of fallback models to try."""
        fallbacks = [cls.RESERVE_1, cls.RESERVE_2, cls.RESERVE_3]
        # Remove primary from fallbacks if present
        return [m for m in fallbacks if m != primary_model]


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
        
        # === AI Models (using ModelRegistry - 2026 models) ===
        self.models = ModelRegistry()
        
        # Override defaults from environment if set
        self.ai_model_fast: str = os.getenv("AI_MODEL_FAST", ModelRegistry.MODEL_CATEGORIZATION)
        self.ai_model_smart: str = os.getenv("AI_MODEL_SMART", ModelRegistry.MODEL_ANALYSIS)
        self.ai_model_conversation: str = os.getenv("AI_MODEL_CONVERSATION", ModelRegistry.MODEL_CONVERSATION)
        self.ai_model_planning: str = os.getenv("AI_MODEL_PLANNING", ModelRegistry.MODEL_PLANNING)
        self.ai_model_whisper: str = os.getenv("AI_MODEL_WHISPER", ModelRegistry.MODEL_WHISPER)
        
        # AI settings
        self.ai_temperature: float = float(os.getenv("AI_TEMPERATURE", "0.3"))
        self.ai_max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "1024"))
        self.ai_timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
        
        # Fallback settings
        self.ai_enable_fallback: bool = os.getenv("AI_ENABLE_FALLBACK", "true").lower() == "true"
        self.ai_max_retries: int = int(os.getenv("AI_MAX_RETRIES", "3"))
        
        # === API Settings ===
        # CORS origins - defaults for local dev, can be overridden via CORS_ORIGINS env var
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            # Parse JSON array or comma-separated list
            import json
            try:
                self.cors_origins = json.loads(cors_env)
            except json.JSONDecodeError:
                self.cors_origins = [origin.strip() for origin in cors_env.split(",")]
        else:
            self.cors_origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        self.api_version: str = "v1"
        
        # === Rate Limiting (Groq Free Tier 2026) ===
        # 30 RPM, 14,400 RPD
        self.rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    
    def get_model(self, task_type: str) -> str:
        """Get the appropriate model for a task type."""
        return self.models.get_model_for_task(task_type)
    
    def get_fallbacks(self, model: str) -> List[str]:
        """Get fallback models for a given primary model."""
        return self.models.get_fallback_chain(model)
    
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
