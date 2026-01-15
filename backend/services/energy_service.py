"""Energy service for tracking and analyzing energy patterns."""
import json
import re
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .groq_service import call_groq
from database import execute_query


def get_time_block(hour: int = None) -> str:
    """Get time block based on hour of day."""
    if hour is None:
        hour = datetime.now().hour
    
    if 5 <= hour < 9:
        return 'morning'
    elif 9 <= hour < 12:
        return 'midday'
    elif 12 <= hour < 17:
        return 'afternoon'
    elif 17 <= hour < 21:
        return 'evening'
    else:
        return 'night'


def get_today_logs() -> List[Dict]:
    """Get all energy logs from today."""
    today = datetime.now().strftime("%Y-%m-%d")
    return execute_query(
        "SELECT * FROM energy_logs WHERE logged_at LIKE ? ORDER BY logged_at ASC",
        (f"{today}%",)
    )


def get_recent_logs(days: int = 7) -> List[Dict]:
    """Get energy logs from the last N days."""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return execute_query(
        "SELECT * FROM energy_logs WHERE logged_at >= ? ORDER BY logged_at DESC",
        (start_date,)
    )


def calculate_averages(logs: List[Dict]) -> Dict[str, float]:
    """Calculate average levels across logs."""
    if not logs:
        return {}
    
    totals = {'energy': 0, 'focus': 0, 'mood': 0, 'stress': 0}
    counts = {'energy': 0, 'focus': 0, 'mood': 0, 'stress': 0}
    
    for log in logs:
        if log.get('energy_level'):
            totals['energy'] += log['energy_level']
            counts['energy'] += 1
        if log.get('focus_level'):
            totals['focus'] += log['focus_level']
            counts['focus'] += 1
        if log.get('mood_level'):
            totals['mood'] += log['mood_level']
            counts['mood'] += 1
        if log.get('stress_level'):
            totals['stress'] += log['stress_level']
            counts['stress'] += 1
    
    return {
        key: round(totals[key] / counts[key], 1) if counts[key] > 0 else None
        for key in totals
    }


def get_averages_by_time_block(logs: List[Dict]) -> Dict[str, Dict]:
    """Calculate averages grouped by time block."""
    blocks = {}
    
    for log in logs:
        block = log.get('time_block')
        if not block:
            continue
        
        if block not in blocks:
            blocks[block] = {'logs': [], 'energy': [], 'focus': []}
        
        blocks[block]['logs'].append(log)
        if log.get('energy_level'):
            blocks[block]['energy'].append(log['energy_level'])
        if log.get('focus_level'):
            blocks[block]['focus'].append(log['focus_level'])
    
    result = {}
    for block, data in blocks.items():
        result[block] = {
            'avg_energy': round(sum(data['energy']) / len(data['energy']), 1) if data['energy'] else None,
            'avg_focus': round(sum(data['focus']) / len(data['focus']), 1) if data['focus'] else None,
            'log_count': len(data['logs'])
        }
    
    return result


PATTERNS_PROMPT = """Analyze these energy logs and identify patterns. Return ONLY valid JSON.

Energy logs (last 30 days):
{logs_json}

Identify:
1. Peak energy times
2. Low energy times
3. Correlations (sleep, caffeine, exercise → energy/focus)
4. Recommendations

Return format:
{{
  "peak_times": [
    {{"time_block": "morning", "average_energy": 4.2, "confidence": 0.85, "best_for": ["deep work"]}}
  ],
  "low_times": [
    {{"time_block": "afternoon", "average_energy": 2.5, "suggestion": "Light tasks"}}
  ],
  "correlations": [
    {{"factor": "sleep_hours", "impact": "positive", "finding": "More sleep = higher energy"}}
  ],
  "recommendations": [
    "Schedule deep work in the morning",
    "Take a break after lunch"
  ],
  "insight": "You're a morning person with a post-lunch dip."
}}"""


def analyze_patterns() -> Dict[str, Any]:
    """AI analyzes energy patterns."""
    logs = get_recent_logs(30)
    
    if len(logs) < 5:
        return {
            "message": "Not enough data yet. Log your energy for at least 5 days to see patterns.",
            "logs_count": len(logs)
        }
    
    # Prepare data for AI
    logs_for_ai = []
    for log in logs:
        logs_for_ai.append({
            "time_block": log.get('time_block'),
            "energy": log.get('energy_level'),
            "focus": log.get('focus_level'),
            "mood": log.get('mood_level'),
            "stress": log.get('stress_level'),
            "sleep": log.get('sleep_hours'),
            "caffeine": log.get('caffeine'),
            "exercise": log.get('exercise')
        })
    
    prompt = PATTERNS_PROMPT.format(logs_json=json.dumps(logs_for_ai, indent=2))
    response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.4)
    
    try:
        patterns = json.loads(response)
        return patterns
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Fallback with basic calculations
        block_avgs = get_averages_by_time_block(logs)
        return {
            "peak_times": [
                {"time_block": block, "average_energy": data['avg_energy']}
                for block, data in sorted(block_avgs.items(), key=lambda x: x[1].get('avg_energy', 0) or 0, reverse=True)[:2]
            ],
            "recommendations": ["Log more data to get personalized insights"],
            "insight": "Keep logging to discover your patterns!"
        }


def get_best_time_for_task(task_type: str) -> Dict[str, Any]:
    """Suggest best time for a task type based on patterns."""
    logs = get_recent_logs(14)
    block_avgs = get_averages_by_time_block(logs)
    
    task_recommendations = {
        'deep_work': {'needs': 'high_energy_focus', 'fallback': 'morning'},
        'meetings': {'needs': 'medium_energy', 'fallback': 'midday'},
        'creative': {'needs': 'high_mood', 'fallback': 'morning'},
        'admin': {'needs': 'low_energy', 'fallback': 'afternoon'}
    }
    
    task_config = task_recommendations.get(task_type, task_recommendations['admin'])
    
    # Find best block
    best_block = task_config['fallback']
    best_score = 0
    
    for block, data in block_avgs.items():
        score = (data.get('avg_energy') or 3) + (data.get('avg_focus') or 3)
        if task_type == 'admin':
            # For admin, prefer lower energy times
            score = 10 - score
        if score > best_score:
            best_score = score
            best_block = block
    
    return {
        "task_type": task_type,
        "best_time_block": best_block,
        "block_data": block_avgs.get(best_block, {}),
        "confidence": "high" if len(logs) > 10 else "low"
    }
