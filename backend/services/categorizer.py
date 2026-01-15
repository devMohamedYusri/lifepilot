"""AI Categorization service using Groq."""
import json
import re
from typing import Dict, Any
from .groq_service import call_groq
from .pii_stripper import strip_pii, restore_pii


CATEGORIZATION_PROMPT = """Analyze this input and categorize it. Return ONLY valid JSON, no explanation.

Input: "{sanitized_input}"

Categories:
- task: Something the user needs to do
- waiting_for: Something the user is waiting for from someone else
- decision: A decision the user needs to make
- note: Information to remember, no action needed
- life_admin: Recurring life maintenance (appointments, renewals, bills)

Return format:
{{
  "type": "task|waiting_for|decision|note|life_admin",
  "priority": "high|medium|low",
  "energy_required": "high|medium|low",
  "context": "work|personal|health|finance|social",
  "due_date": "YYYY-MM-DD or null",
  "person_involved": "name or null",
  "summary": "brief 5-10 word summary",
  "next_action": "specific next action if task, else null",
  "follow_up_days": "for waiting_for: 1 if urgent, 3 if normal, 7 if low priority, else null",
  "recurrence_pattern": "for life_admin: daily|weekly|monthly|yearly if recurring, else null",
  "recurrence_interval": "number of periods between recurrences, default 1"
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
    
    # Try to find raw JSON object
    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Return defaults if all parsing fails
    return {
        "type": "note",
        "priority": "medium",
        "energy_required": "medium",
        "context": "personal",
        "due_date": None,
        "person_involved": None,
        "summary": response[:50] if response else "Unable to categorize",
        "next_action": None
    }


def categorize_input(raw_content: str) -> Dict[str, Any]:
    """
    Categorize user input using AI.
    
    Args:
        raw_content: The raw text input from the user
        
    Returns:
        Dictionary with categorization results
    """
    # Strip PII before sending to AI
    sanitized_input, pii_mapping = strip_pii(raw_content)
    
    # Build prompt
    prompt = CATEGORIZATION_PROMPT.format(sanitized_input=sanitized_input)
    
    # Call AI
    response = call_groq(prompt, model="llama-3.1-8b-instant", temperature=0.3)
    
    # Parse response
    result = extract_json_from_response(response)
    
    # Restore PII in summary and next_action if present
    if result.get("summary"):
        result["summary"] = restore_pii(result["summary"], pii_mapping)
    if result.get("next_action"):
        result["next_action"] = restore_pii(result["next_action"], pii_mapping)
    if result.get("person_involved"):
        result["person_involved"] = restore_pii(result["person_involved"], pii_mapping)
    
    # Validate and normalize values
    valid_types = ["task", "waiting_for", "decision", "note", "life_admin"]
    valid_priorities = ["high", "medium", "low"]
    valid_energy = ["high", "medium", "low"]
    
    if result.get("type") not in valid_types:
        result["type"] = "note"
    if result.get("priority") not in valid_priorities:
        result["priority"] = "medium"
    if result.get("energy_required") not in valid_energy:
        result["energy_required"] = "medium"
    
    # Phase 2: Set default follow-up days for waiting_for items
    if result.get("type") == "waiting_for" and not result.get("follow_up_days"):
        if result.get("priority") == "high":
            result["follow_up_days"] = 1
        elif result.get("priority") == "low":
            result["follow_up_days"] = 7
        else:
            result["follow_up_days"] = 3
    
    # Phase 2: Validate recurrence pattern
    valid_patterns = ["daily", "weekly", "monthly", "yearly", None]
    if result.get("recurrence_pattern") not in valid_patterns:
        result["recurrence_pattern"] = None
    
    return result

