"""Review service for AI-powered weekly summaries."""
import json
import re
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .groq_service import call_groq
from database import execute_query


REVIEW_SUMMARY_PROMPT = """Generate a weekly review summary. Return ONLY valid JSON.

This week's activity:
- Tasks completed: {items_completed}
- Bookmarks read: {bookmarks_read}
- Decisions made: {decisions_made}
- Follow-ups sent: {follow_ups}

Completed tasks this week:
{completed_items}

Provide:
1. Key accomplishments (3-5 bullet points)
2. Themes/patterns you notice
3. Encouragement message
4. 3 reflection prompts for the user

Return format:
{{
  "accomplishments": ["Accomplished X", "Made progress on Y"],
  "themes": ["Focus on career growth", "Building connections"],
  "insights": "You spent most energy on work decisions this week",
  "encouragement": "Great week! You cleared a lot of backlog.",
  "reflection_prompts": [
    "What was your biggest win this week?",
    "What would you do differently?",
    "What's your main focus for next week?"
  ]
}}"""


def get_week_bounds(offset_weeks: int = 0) -> tuple:
    """Get start/end dates for a week (offset from current)."""
    today = datetime.now()
    # Start of current week (Monday)
    start = today - timedelta(days=today.weekday() + (offset_weeks * 7))
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    # End of week (Sunday)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start.isoformat(), end.isoformat()


def calculate_stats(week_start: str, week_end: str) -> Dict[str, Any]:
    """Calculate weekly stats from all tables."""
    stats = {
        "items_completed": 0,
        "bookmarks_read": 0,
        "decisions_made": 0,
        "follow_ups": 0,
        "completed_items": []
    }
    
    # Items completed this week
    items = execute_query("""
        SELECT * FROM items 
        WHERE status = 'done' 
        AND created_at >= ? AND created_at <= ?
        ORDER BY created_at DESC
    """, (week_start, week_end))
    stats["items_completed"] = len(items)
    stats["completed_items"] = [
        {"type": i.get("type"), "summary": i.get("ai_summary") or i.get("raw_content", "")[:50]}
        for i in items[:10]
    ]
    
    # Bookmarks read (status=completed)
    try:
        bookmarks = execute_query("""
            SELECT COUNT(*) as count FROM bookmarks 
            WHERE status = 'completed'
            AND created_at >= ? AND created_at <= ?
        """, (week_start, week_end))
        stats["bookmarks_read"] = bookmarks[0]["count"] if bookmarks else 0
    except:
        pass
    
    # Decisions made (status=decided or completed)
    try:
        decisions = execute_query("""
            SELECT COUNT(*) as count FROM decisions 
            WHERE status IN ('decided', 'awaiting_outcome', 'completed')
            AND created_at >= ? AND created_at <= ?
        """, (week_start, week_end))
        stats["decisions_made"] = decisions[0]["count"] if decisions else 0
    except:
        pass
    
    # Follow-ups made (items with follow_up_count > 0)
    try:
        follow_ups = execute_query("""
            SELECT SUM(follow_up_count) as total FROM items 
            WHERE follow_up_count > 0
            AND created_at >= ? AND created_at <= ?
        """, (week_start, week_end))
        stats["follow_ups"] = follow_ups[0]["total"] or 0 if follow_ups else 0
    except:
        pass
    
    return stats


def generate_ai_summary(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Generate AI summary from weekly stats."""
    completed_items_text = "\n".join([
        f"- [{i['type']}] {i['summary']}" for i in stats.get("completed_items", [])
    ]) or "No items completed"
    
    prompt = REVIEW_SUMMARY_PROMPT.format(
        items_completed=stats["items_completed"],
        bookmarks_read=stats["bookmarks_read"],
        decisions_made=stats["decisions_made"],
        follow_ups=stats["follow_ups"],
        completed_items=completed_items_text
    )
    
    response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.5)
    
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
            "accomplishments": [f"Completed {stats['items_completed']} items"],
            "themes": ["Productive week"],
            "insights": "Keep up the momentum!",
            "encouragement": "Great progress this week!",
            "reflection_prompts": [
                "What was your biggest win?",
                "What would you do differently?",
                "What's your focus for next week?"
            ]
        }


def generate_review(offset_weeks: int = 0) -> Dict[str, Any]:
    """Generate full weekly review."""
    week_start, week_end = get_week_bounds(offset_weeks)
    
    # Check if review already exists
    existing = execute_query(
        "SELECT * FROM reviews WHERE week_start = ?", (week_start,)
    )
    if existing:
        return dict(existing[0])
    
    # Calculate stats
    stats = calculate_stats(week_start, week_end)
    
    # Generate AI summary
    ai_content = generate_ai_summary(stats)
    
    return {
        "week_start": week_start,
        "week_end": week_end,
        "items_completed": stats["items_completed"],
        "bookmarks_read": stats["bookmarks_read"],
        "decisions_made": stats["decisions_made"],
        "follow_ups": stats["follow_ups"],
        "accomplishments": ai_content.get("accomplishments", []),
        "themes": ai_content.get("themes", []),
        "insights": ai_content.get("insights", ""),
        "encouragement": ai_content.get("encouragement", ""),
        "reflection_prompts": ai_content.get("reflection_prompts", []),
        "is_new": True
    }
