"""
Groq API service for AI completions with multi-model support and fallback logic.

Model Strategy:
- 5 Primary models for specific tasks (categorization, analysis, conversation, planning, transcription)
- 3 Reserve models for fallback when primary fails
- Automatic retry with exponential backoff
- Fallback to reserve models on repeated failures
"""
import time
import logging
from typing import Optional, List
import groq
from groq import Groq

# Import from centralized config
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import settings, ModelRegistry
from core.exceptions import AIServiceError, RateLimitError, AuthenticationError

logger = logging.getLogger(__name__)

# Initialize client lazily
_client = None


def get_client() -> Groq:
    """Get or create Groq client."""
    global _client
    if _client is None:
        if not settings.groq_api_key:
            # Raise configuration error if API key is missing
            raise AIServiceError(
                message="GROQ_API_KEY environment variable is not set",
                code="config_missing",
                status_code=500
            )
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def call_groq(
    prompt: str, 
    model: Optional[str] = None,
    task_type: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    use_fallback: bool = True,
    system_prompt: Optional[str] = None
) -> str:
    """
    Call Groq API with the given prompt, with retry and fallback logic.
    """
    client = get_client()
    
    # Determine primary model
    if model:
        primary_model = model
    elif task_type:
        primary_model = settings.get_model(task_type)
    else:
        primary_model = settings.ai_model_fast
    
    # Build model chain: primary -> fallbacks
    models_to_try = [primary_model]
    if use_fallback and settings.ai_enable_fallback:
        models_to_try.extend(settings.get_fallbacks(primary_model))
    
    # Use settings defaults if not specified
    temperature = temperature if temperature is not None else settings.ai_temperature
    max_tokens = max_tokens or settings.ai_max_tokens
    
    # Build messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    last_exception = None
    
    for model_name in models_to_try:
        logger.info(f"Trying model: {model_name}")
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                result = response.choices[0].message.content
                
                # Log success
                if model_name != primary_model:
                    logger.info(f"Fallback model {model_name} succeeded")
                    
                return result
                
            except groq.RateLimitError as e:
                last_exception = e
                logger.warning(f"Rate limit hit on {model_name}, trying next model...")
                break  # Skip to next model immediately
                
            except groq.AuthenticationError as e:
                # Auth error is fatal, do not retry
                logger.error(f"Authentication failed: {e}")
                raise AuthenticationError("Invalid Groq API Key")
                
            except groq.APIConnectionError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Connection error on {model_name}: {e}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"Connection error on {model_name} persist after retries.")
            
            except groq.BadRequestError as e:
                # Bad request (e.g. context length) - might work on another model?
                last_exception = e
                if "context_length_exceeded" in str(e).lower():
                     logger.warning(f"Context length exceeded on {model_name}, trying next model...")
                     break # Try next model (maybe it has larger context)
                
                logger.error(f"Bad request: {e}")
                raise AIServiceError(message=str(e), code="bad_request", status_code=400)

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on {model_name}: {e}")
                if attempt < max_retries - 1:
                     time.sleep(retry_delay)
                
    # All models failed
    logger.error(f"All models failed. Last error: {last_exception}")
    
    # Map last exception to LifePilotException
    if isinstance(last_exception, groq.RateLimitError):
        raise RateLimitError(retry_after=60)
    elif isinstance(last_exception, groq.APIConnectionError):
        raise AIServiceError(message="Failed to connect to AI service", code="connection_error")
    else:
        raise AIServiceError(message=f"AI Service Failure: {str(last_exception)}", code="service_failure")


def call_groq_for_task(
    task_type: str,
    prompt: str,
    **kwargs
) -> str:
    """
    Convenience function to call Groq with automatic model selection for a task type.
    
    Task types:
    - categorization: Fast model for item categorization
    - analysis: Smart model for bookmark/pattern analysis
    - conversation: Balanced model for agent chat
    - planning: Reasoning model for decisions/reviews
    """
    return call_groq(prompt, task_type=task_type, **kwargs)


# === Task-specific convenience functions ===

def categorize(prompt: str, **kwargs) -> str:
    """Quick categorization using fast model."""
    return call_groq(prompt, task_type="categorization", **kwargs)


def analyze(prompt: str, **kwargs) -> str:
    """Detailed analysis using smart model."""
    return call_groq(prompt, task_type="analysis", **kwargs)


def chat(prompt: str, system_prompt: str = None, **kwargs) -> str:
    """Conversational response using chat model."""
    return call_groq(prompt, task_type="conversation", system_prompt=system_prompt, **kwargs)


def plan(prompt: str, **kwargs) -> str:
    """Planning/reasoning using planning model."""
    return call_groq(prompt, task_type="planning", **kwargs)


def get_available_models() -> dict:
    """Get information about available models (2026 lineup)."""
    return {
        "primary_models": {
            "categorization": ModelRegistry.MODEL_CATEGORIZATION,
            "analysis": ModelRegistry.MODEL_ANALYSIS,
            "conversation": ModelRegistry.MODEL_CONVERSATION,
            "planning": ModelRegistry.MODEL_PLANNING,
            "transcription": ModelRegistry.MODEL_WHISPER,
        },
        "reserve_models": [
            ModelRegistry.RESERVE_1,
            ModelRegistry.RESERVE_2,
            ModelRegistry.RESERVE_3,
        ],
        "model_info": {
            name: {
                "context_window": config.context_window,
                "tokens_per_minute": config.tokens_per_minute,
                "best_for": config.best_for,
            }
            for name, config in ModelRegistry.MODELS.items()
        }
    }

