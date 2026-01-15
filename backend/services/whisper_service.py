"""Groq Whisper API service for voice transcription."""
import os
import logging
import httpx
from typing import Dict, Any, Optional, BinaryIO
from datetime import datetime

logger = logging.getLogger(__name__)

# Groq API configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Available Whisper models
WHISPER_MODELS = {
    "whisper-large-v3": {
        "name": "Whisper Large V3",
        "description": "Highest accuracy, slower processing",
        "speed": "slow",
        "accuracy": "highest"
    },
    "whisper-large-v3-turbo": {
        "name": "Whisper Large V3 Turbo",
        "description": "Best balance of speed and accuracy (recommended)",
        "speed": "fast",
        "accuracy": "high"
    },
    "distil-whisper-large-v3-en": {
        "name": "Distil Whisper Large V3 (English)",
        "description": "Fastest, optimized for English",
        "speed": "fastest",
        "accuracy": "good",
        "language": "en"
    }
}

DEFAULT_MODEL = "whisper-large-v3-turbo"

# Supported audio formats
SUPPORTED_FORMATS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


def get_available_models() -> Dict[str, Any]:
    """Get available Whisper models with descriptions."""
    return {
        "models": WHISPER_MODELS,
        "default": DEFAULT_MODEL
    }


def validate_audio(filename: str, file_size: int) -> Dict[str, Any]:
    """
    Validate audio file for Groq Whisper API.
    
    Args:
        filename: Name of the audio file
        file_size: Size of the file in bytes
        
    Returns:
        Validation result with success status and any errors
    """
    # Check file extension
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if not extension:
        return {
            "valid": False,
            "error": "No file extension provided",
            "supported_formats": SUPPORTED_FORMATS
        }
    
    if extension not in SUPPORTED_FORMATS:
        return {
            "valid": False,
            "error": f"Unsupported format: {extension}",
            "supported_formats": SUPPORTED_FORMATS
        }
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        return {
            "valid": False,
            "error": f"File too large: {file_size / 1024 / 1024:.1f}MB (max: 25MB)",
            "max_size_mb": 25
        }
    
    if file_size == 0:
        return {
            "valid": False,
            "error": "Audio file is empty"
        }
    
    return {"valid": True}


async def transcribe_audio(
    audio_file: BinaryIO,
    filename: str,
    model: str = None,
    language: str = None,
    temperature: float = 0
) -> Dict[str, Any]:
    """
    Transcribe audio using Groq Whisper API.
    
    Args:
        audio_file: Audio file object
        filename: Original filename
        model: Whisper model to use (default: whisper-large-v3-turbo)
        language: Language code (e.g., 'en') or None for auto-detect
        temperature: Sampling temperature (0-1)
        
    Returns:
        Transcription result with text and metadata
    """
    if not GROQ_API_KEY:
        return {
            "success": False,
            "error": "GROQ_API_KEY not configured"
        }
    
    model = model or DEFAULT_MODEL
    
    if model not in WHISPER_MODELS:
        return {
            "success": False,
            "error": f"Invalid model: {model}",
            "available_models": list(WHISPER_MODELS.keys())
        }
    
    start_time = datetime.now()
    
    try:
        # Read file content
        audio_content = audio_file.read()
        
        # Validate
        validation = validate_audio(filename, len(audio_content))
        if not validation["valid"]:
            return {"success": False, **validation}
        
        # Prepare multipart form data
        files = {
            "file": (filename, audio_content, "audio/webm")
        }
        data = {
            "model": model,
            "response_format": "json",
            "temperature": str(temperature)
        }
        
        if language:
            data["language"] = language
        
        # Send to Groq API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                },
                files=files,
                data=data
            )
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "text": result.get("text", ""),
                "model": model,
                "processing_ms": int(processing_time),
                "audio_size_bytes": len(audio_content)
            }
        elif response.status_code == 429:
            return {
                "success": False,
                "error": "Rate limit exceeded. Please wait a moment and try again.",
                "retry_after": response.headers.get("Retry-After", "60")
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Invalid API key. Check GROQ_API_KEY configuration."
            }
        else:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("error", {}).get("message", error_detail)
            except:
                pass
            
            return {
                "success": False,
                "error": f"Transcription failed: {error_detail}",
                "status_code": response.status_code
            }
            
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Transcription timed out. Try with a shorter recording."
        }
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {
            "success": False,
            "error": f"Transcription failed: {str(e)}"
        }


def detect_multiple_items(text: str) -> list:
    """
    Detect if transcription contains multiple items.
    
    Splits on natural phrase separators like "and also", "next", "another thing".
    
    Args:
        text: Transcribed text
        
    Returns:
        List of detected items
    """
    if not text:
        return []
    
    # Common separators in natural speech
    separators = [
        " and also ",
        " also ",
        " next ",
        " another thing ",
        " one more ",
        " plus ",
        ". Also,",
        ". Next,",
        ". Another thing,",
    ]
    
    items = [text]
    
    for separator in separators:
        new_items = []
        for item in items:
            if separator.lower() in item.lower():
                # Case-insensitive split
                idx = item.lower().find(separator.lower())
                part1 = item[:idx].strip()
                part2 = item[idx + len(separator):].strip()
                
                if part1:
                    new_items.append(part1)
                if part2:
                    new_items.append(part2)
            else:
                new_items.append(item)
        items = new_items
    
    # Clean up items
    items = [item.strip().strip('.').strip() for item in items if item.strip()]
    
    return items if len(items) > 1 else [text]
