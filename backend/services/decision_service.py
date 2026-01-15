"""Decision service for AI-powered decision expansion and insights."""
import json
import re
from typing import Dict, Any, List
from .groq_service import call_groq


EXPAND_DECISION_PROMPT = """Help structure this decision. Return ONLY valid JSON.

Decision: "{decision_text}"

Analyze and suggest:
1. Rephrase as clear decision question
2. Generate 2-4 realistic options
3. For each option, list 2-3 pros and cons
4. Identify who might be affected (stakeholders)
5. Suggest key questions to consider
6. Recommend if this is time-sensitive

Return format:
{{
  "decision_question": "Should I...",
  "situation": "Brief context of the situation",
  "options": [
    {{
      "option": "Option A description",
      "pros": ["pro 1", "pro 2"],
      "cons": ["con 1", "con 2"]
    }},
    {{
      "option": "Option B description", 
      "pros": ["pro 1", "pro 2"],
      "cons": ["con 1", "con 2"]
    }}
  ],
  "stakeholders": ["self", "family", "employer"],
  "key_questions": [
    "What is the worst case scenario?",
    "What would I regret more?"
  ],
  "suggested_tags": ["career", "financial"],
  "time_sensitive": true,
  "suggested_deadline": "2024-01-15 or null"
}}"""


INSIGHTS_PROMPT = """Analyze these past decisions and provide insights. Return ONLY valid JSON.

Completed decisions:
{decisions_json}

Analyze:
1. What patterns appear in high-rated outcomes (4-5)?
2. What patterns appear in low-rated outcomes (1-2)?
3. How well do confidence levels predict actual outcomes?
4. Which types of decisions does this person make well/poorly?
5. What specific advice would help this person?

Return format:
{{
  "total_analyzed": 15,
  "average_outcome": 3.5,
  "patterns": {{
    "successful": ["Took time to consider options", "Consulted others"],
    "unsuccessful": ["Rushed decisions", "Ignored gut feeling"]
  }},
  "confidence_accuracy": "Your confidence often overestimates outcomes by 1 point",
  "strengths": ["Career decisions", "Financial planning"],
  "growth_areas": ["Relationship decisions", "Quick judgments"],
  "top_advice": [
    "Sleep on major decisions - your rushed choices score 2 points lower",
    "Trust your analysis more in financial matters"
  ],
  "encouragement": "You're learning! Your recent decisions show improvement."
}}"""


def expand_decision(decision_text: str) -> Dict[str, Any]:
    """Use AI to expand and analyze a decision with pros/cons."""
    prompt = EXPAND_DECISION_PROMPT.format(decision_text=decision_text)
    response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.4)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        return {
            "decision_question": decision_text,
            "situation": "Unable to analyze",
            "options": [],
            "stakeholders": [],
            "key_questions": [],
            "suggested_tags": [],
            "time_sensitive": False,
            "suggested_deadline": None
        }


def generate_insights(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate AI insights from past decisions with pattern analysis."""
    if not decisions or len(decisions) < 2:
        return {
            "total_analyzed": len(decisions) if decisions else 0,
            "average_outcome": None,
            "patterns": {"successful": [], "unsuccessful": []},
            "confidence_accuracy": None,
            "strengths": [],
            "growth_areas": [],
            "top_advice": ["Record more decisions and outcomes to get personalized insights"],
            "encouragement": "Start tracking decisions to discover your patterns!"
        }
    
    # Prepare summary for AI
    decisions_summary = []
    for d in decisions:
        decisions_summary.append({
            "situation": d.get("situation"),
            "chosen_option": d.get("chosen_option"),
            "reasoning": d.get("reasoning"),
            "confidence": d.get("confidence"),
            "expected_outcome": d.get("expected_outcome"),
            "actual_outcome": d.get("actual_outcome"),
            "rating": d.get("rating"),
            "expectation_matched": d.get("expectation_matched"),
            "lessons": d.get("lessons"),
            "tags": d.get("tags")
        })
    
    prompt = INSIGHTS_PROMPT.format(decisions_json=json.dumps(decisions_summary[:20], indent=2))
    response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.4)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        return {
            "total_analyzed": len(decisions),
            "average_outcome": None,
            "patterns": {"successful": [], "unsuccessful": []},
            "confidence_accuracy": None,
            "strengths": [],
            "growth_areas": [],
            "top_advice": ["Unable to analyze patterns currently"],
            "encouragement": "Keep recording decisions!"
        }
