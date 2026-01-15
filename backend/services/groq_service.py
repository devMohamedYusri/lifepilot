"""Groq API service for AI completions with retry logic."""
import time
import logging
from typing import Optional
from groq import Groq

# Import from centralized config instead of dotenv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import settings

logger = logging.getLogger(__name__)

# Initialize client lazily
_client = None


def get_client() -> Groq:
    """Get or create Groq client."""
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def call_groq(
    prompt: str, 
    model: Optional[str] = None, 
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> str:
    """
    Call Groq API with the given prompt, with retry logic.
    
    Args:
        prompt: The user prompt to send
        model: Model to use (default from settings)
        temperature: Sampling temperature (default from settings)
        max_tokens: Maximum tokens in response (default from settings)
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)
        
    Returns:
        The model's response text
        
    Raises:
        Exception: If all retries fail
    """
    client = get_client()
    
    # Use settings defaults if not specified
    model = model or settings.ai_model_fast
    temperature = temperature if temperature is not None else settings.ai_temperature
    max_tokens = max_tokens or settings.ai_max_tokens
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
            
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Groq API call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Groq API call failed after {max_retries} attempts: {e}")
    
    raise last_exception

