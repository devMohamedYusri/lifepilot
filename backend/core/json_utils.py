"""JSON parsing utilities for AI responses."""
import json
import re
from typing import Dict, Any, Optional, TypeVar, Type
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Dict[str, Any])


def extract_json_from_response(
    response: str, 
    default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract JSON from AI response, handling potential markdown formatting.
    
    Args:
        response: Raw AI response text
        default: Default value if JSON extraction fails
        
    Returns:
        Parsed JSON dictionary or default value
    """
    if not response:
        return default or {}
    
    # Try direct parse first
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON object (greedy match)
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Log warning and return default
    logger.warning(f"Could not parse JSON from response: {response[:100]}...")
    return default or {}


def safe_json_loads(
    text: str, 
    default: Optional[T] = None
) -> T:
    """
    Safely parse JSON string with fallback to default.
    
    Args:
        text: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed value or default
    """
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def validate_and_normalize(
    data: Dict[str, Any],
    schema: Dict[str, tuple],
    defaults: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate and normalize parsed JSON data against allowed values.
    
    Args:
        data: Raw parsed JSON data
        schema: Dict mapping field names to (allowed_values, default_value) tuples
        defaults: Additional default values for missing fields
        
    Returns:
        Normalized data with validated values
        
    Example:
        schema = {
            "priority": (["high", "medium", "low"], "medium"),
            "type": (["task", "note"], "note")
        }
        normalized = validate_and_normalize(data, schema)
    """
    result = dict(data)
    
    # Apply validation from schema
    for field, (allowed_values, default_value) in schema.items():
        if result.get(field) not in allowed_values:
            result[field] = default_value
    
    # Apply additional defaults
    if defaults:
        for key, value in defaults.items():
            if key not in result or result[key] is None:
                result[key] = value
    
    return result
