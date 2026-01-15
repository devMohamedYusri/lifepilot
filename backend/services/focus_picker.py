"""Focus picker service for Today's Focus AI selection."""
import json
import re
from datetime import date
from typing import Dict, Any, List
from .groq_service import call_groq


FOCUS_PROMPT = """You are a productivity assistant. Select the 3-5 most important items to focus on today.

Current items:
{items_json}

Today's date: {today}

Consider:
1. Overdue items (highest priority)
2. Due today
3. High priority items
4. Mix of contexts to avoid burnout
5. Start with a low-energy win if many high-energy tasks

Return ONLY valid JSON:
{{
  "focus_items": [
    {{"id": 1, "reason": "brief reason why this is important today"}}
  ],
  "encouragement": "brief motivational message for the day"
}}"""


def extract_json_from_response(response: str) -> Dict[str, Any]:
    """Extract JSON from AI response, handling potential markdown formatting."""
    # Try direct parse first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON object with arrays
    json_match = re.search(r'\{[^{}]*"focus_items"\s*:\s*\[.*?\][^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Return empty focus if parsing fails
    return {
        "focus_items": [],
        "encouragement": "Let's make today count!"
    }


def pick_focus_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Use AI to select the most important items for today's focus.
    
    Args:
        items: List of active items from the database
        
    Returns:
        Dictionary with focus_items and encouragement
    """
    if not items:
        return {
            "focus_items": [],
            "encouragement": "No active items! Time to capture some tasks in your inbox."
        }
    
    # Prepare items for AI (only relevant fields, no raw PII-containing content)
    items_for_ai = []
    for item in items:
        items_for_ai.append({
            "id": item["id"],
            "summary": item.get("ai_summary") or item.get("raw_content", "")[:50],
            "type": item.get("type"),
            "priority": item.get("priority"),
            "energy_required": item.get("energy_required"),
            "context": item.get("context"),
            "due_date": item.get("due_date"),
        })
    
    # Build prompt
    today = date.today().isoformat()
    items_json = json.dumps(items_for_ai, indent=2)
    prompt = FOCUS_PROMPT.format(items_json=items_json, today=today)
    
    # Call AI with larger model for better reasoning
    response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.4)
    
    # Parse response
    result = extract_json_from_response(response)
    
    # Validate focus items have valid IDs
    valid_ids = {item["id"] for item in items}
    result["focus_items"] = [
        fi for fi in result.get("focus_items", [])
        if fi.get("id") in valid_ids
    ]
    
    # Ensure we have encouragement
    if not result.get("encouragement"):
        result["encouragement"] = "You've got this! Focus on one thing at a time."
    
    return result
