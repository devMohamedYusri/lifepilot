"""
Proactive Service for autonomous agent operations.

Handles morning briefings, proactive checks, and automated reminders.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from database import execute_query, execute_write
from services.notification_service import create_notification

logger = logging.getLogger(__name__)


def generate_morning_briefing(params: Dict = None) -> Dict:
    """Generate morning briefing with today's focus items."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get items due today
    due_today = execute_query(
        "SELECT * FROM items WHERE due_date = ? AND status = 'active'", (today,)
    )
    
    # Get overdue items
    overdue = execute_query(
        "SELECT * FROM items WHERE due_date < ? AND status = 'active'", (today,)
    )
    
    # Get high priority items
    high_priority = execute_query(
        "SELECT * FROM items WHERE priority = 'high' AND status = 'active' LIMIT 3"
    )
    
    # Get follow-ups due
    followups = execute_query(
        "SELECT * FROM items WHERE type = 'waiting_for' AND follow_up_date <= ? AND status = 'active'",
        (today,)
    )
    
    # Get calendar events for today
    calendar_events = execute_query("""
        SELECT * FROM calendar_events 
        WHERE date(start_time) = ? 
        ORDER BY start_time ASC
    """, (today,))
    
    # Build briefing message
    parts = [f"Good morning! Here's your focus for {today}:"]
    
    if overdue:
        parts.append(f"⚠️ {len(overdue)} overdue item{'s' if len(overdue) > 1 else ''}")
    
    if due_today:
        parts.append(f"📅 {len(due_today)} item{'s' if len(due_today) > 1 else ''} due today")
    
    if calendar_events:
        parts.append(f"📆 {len(calendar_events)} calendar event{'s' if len(calendar_events) > 1 else ''}")
    
    if followups:
        parts.append(f"📨 {len(followups)} follow-up{'s' if len(followups) > 1 else ''} needed")
    
    if high_priority:
        parts.append("🎯 Top priorities:")
        for item in high_priority[:3]:
            summary = item.get('ai_summary') or item.get('raw_content', '')[:50]
            parts.append(f"  • {summary}")
    
    message = "\n".join(parts)
    
    # Create notification
    create_notification(
        type="daily_briefing",
        title="Morning Briefing",
        message=message,
        priority="medium"
    )
    
    return {
        "status": "success",
        "items_affected": len(due_today) + len(overdue) + len(followups),
        "summary": {
            "due_today": len(due_today),
            "overdue": len(overdue),
            "high_priority": len(high_priority),
            "followups": len(followups),
            "calendar_events": len(calendar_events)
        }
    }


def run_proactive_check(params: Dict = None) -> Dict:
    """Run proactive check for items needing attention."""
    today = datetime.now().strftime("%Y-%m-%d")
    notifications_created = 0
    items_found = 0
    
    # Check for items becoming overdue soon (within 24 hours)
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    upcoming_due = execute_query(
        "SELECT * FROM items WHERE due_date = ? AND status = 'active'", (tomorrow,)
    )
    
    for item in upcoming_due:
        # Check if notification already exists
        existing = execute_query("""
            SELECT id FROM notifications 
            WHERE linked_type = 'item' AND linked_id = ? AND status = 'pending' AND type = 'due_reminder'
        """, (item['id'],))
        
        if not existing:
            summary = item.get('ai_summary') or item.get('raw_content', '')[:50]
            create_notification(
                type="due_reminder",
                title="Due Tomorrow",
                message=f"{summary}",
                priority="medium",
                linked_type="item",
                linked_id=item['id']
            )
            notifications_created += 1
    
    items_found += len(upcoming_due)
    
    # Check for stale waiting-for items (no follow-up in 7+ days)
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    stale_waiting = execute_query("""
        SELECT * FROM items 
        WHERE type = 'waiting_for' AND status = 'active'
        AND (follow_up_date < ? OR follow_up_date IS NULL)
        AND updated_at < ?
        LIMIT 5
    """, (today, week_ago))
    
    if stale_waiting:
        create_notification(
            type="stale_items",
            title=f"{len(stale_waiting)} waiting items need attention",
            message="Some items you're waiting for haven't been followed up recently.",
            priority="low"
        )
        notifications_created += 1
        items_found += len(stale_waiting)
    
    # Check for decisions awaiting outcome
    old_decisions = execute_query("""
        SELECT d.*, i.raw_content, i.ai_summary 
        FROM decisions d
        JOIN items i ON d.item_id = i.id
        WHERE d.status = 'awaiting_outcome'
        AND d.created_at < ?
    """, (week_ago,))
    
    if old_decisions:
        create_notification(
            type="decision_followup",
            title=f"{len(old_decisions)} decisions need outcome recording",
            message="Record outcomes to improve your decision-making insights.",
            priority="low"
        )
        notifications_created += 1
        items_found += len(old_decisions)
    
    # Log activity
    execute_write("""
        INSERT INTO agent_activity_log 
        (activity_type, activity_description, triggered_by, notifications_sent, items_affected, started_at, completed_at)
        VALUES ('proactive_check', 'Checked for items needing attention', 'schedule', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (notifications_created, items_found))
    
    return {
        "status": "success",
        "items_affected": items_found,
        "notifications_sent": notifications_created
    }


def run_contact_check(params: Dict = None) -> Dict:
    """Check for contacts that need reaching out."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get contacts overdue for contact
    overdue_contacts = execute_query("""
        SELECT * FROM contacts 
        WHERE is_active = 1 AND next_contact_date <= ?
        ORDER BY next_contact_date ASC
        LIMIT 5
    """, (today,))
    
    if not overdue_contacts:
        return {"status": "success", "items_affected": 0, "message": "No contacts need attention"}
    
    # Create notification
    contact_names = [c['name'] for c in overdue_contacts[:3]]
    others = len(overdue_contacts) - 3
    
    message = f"Time to reach out to: {', '.join(contact_names)}"
    if others > 0:
        message += f" and {others} more"
    
    create_notification(
        type="contact_reminder",
        title=f"{len(overdue_contacts)} contacts to reach out to",
        message=message,
        priority="low",
        linked_type="contacts"
    )
    
    return {
        "status": "success",
        "items_affected": len(overdue_contacts),
        "contacts": [c['name'] for c in overdue_contacts]
    }


def run_pattern_analysis(params: Dict = None) -> Dict:
    """Refresh pattern analysis."""
    from services.energy_service import analyze_patterns as analyze_energy_patterns
    from services.decision_service import generate_insights
    
    results = {
        "energy_patterns": None,
        "decision_insights": None
    }
    
    try:
        results["energy_patterns"] = analyze_energy_patterns()
    except Exception as e:
        logger.warning(f"Energy pattern analysis failed: {e}")
    
    try:
        decisions = execute_query(
            "SELECT * FROM decisions WHERE status = 'completed' ORDER BY created_at DESC LIMIT 20"
        )
        if decisions:
            results["decision_insights"] = generate_insights(decisions)
    except Exception as e:
        logger.warning(f"Decision insights failed: {e}")
    
    return {
        "status": "success",
        "items_affected": 0,
        "results": results
    }


def run_maintenance(params: Dict = None) -> Dict:
    """Run maintenance tasks."""
    cleaned = 0
    
    # Archive old completed items (> 90 days)
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    execute_write(
        "UPDATE items SET status = 'archived' WHERE status = 'done' AND updated_at < ?",
        (cutoff,)
    )
    
    # Clean old notifications (> 30 days, dismissed)
    notification_cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    execute_write(
        "DELETE FROM notifications WHERE status = 'dismissed' AND created_at < ?",
        (notification_cutoff,)
    )
    
    # Clean old task executions (> 30 days)
    execute_write(
        "DELETE FROM task_executions WHERE created_at < ?",
        (notification_cutoff,)
    )
    
    # Clean old activity log (> 60 days)
    activity_cutoff = (datetime.now() - timedelta(days=60)).isoformat()
    execute_write(
        "DELETE FROM agent_activity_log WHERE created_at < ?",
        (activity_cutoff,)
    )
    
    # Clean completed background jobs
    execute_write(
        "DELETE FROM background_jobs WHERE status IN ('completed', 'cancelled') AND created_at < ?",
        (notification_cutoff,)
    )
    
    return {
        "status": "success",
        "items_affected": cleaned,
        "message": "Maintenance completed"
    }


def get_activity_summary(since: str = None) -> Dict:
    """Get summary of agent activity."""
    if not since:
        since = (datetime.now() - timedelta(hours=24)).isoformat()
    
    activities = execute_query("""
        SELECT * FROM agent_activity_log 
        WHERE started_at >= ?
        ORDER BY started_at DESC
    """, (since,))
    
    total_notifications = sum(a.get('notifications_sent', 0) for a in activities)
    total_items = sum(a.get('items_affected', 0) for a in activities)
    
    by_type = {}
    for a in activities:
        atype = a.get('activity_type', 'unknown')
        by_type[atype] = by_type.get(atype, 0) + 1
    
    return {
        "since": since,
        "total_activities": len(activities),
        "total_notifications_sent": total_notifications,
        "total_items_affected": total_items,
        "by_type": by_type,
        "recent_activities": [
            {
                "type": a['activity_type'],
                "description": a['activity_description'],
                "at": a['started_at']
            }
            for a in activities[:5]
        ]
    }


def generate_evening_review(params: Dict = None) -> Dict:
    """Generate evening review prompt for daily reflection."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get items completed today
    completed_today = execute_query("""
        SELECT * FROM items 
        WHERE status = 'done' AND date(updated_at) = ?
    """, (today,))
    
    # Get items still active
    still_active = execute_query(
        "SELECT COUNT(*) as count FROM items WHERE status = 'active'"
    )
    active_count = still_active[0]['count'] if still_active else 0
    
    # Build reflection message
    parts = ["Good evening! Time for a quick reflection:"]
    
    if completed_today:
        parts.append(f"✅ You completed {len(completed_today)} item{'s' if len(completed_today) > 1 else ''} today!")
    else:
        parts.append("📝 No items completed today - that's okay, tomorrow is a new day.")
    
    parts.append(f"📋 {active_count} items still in progress")
    parts.append("")
    parts.append("Consider: What went well today? What would you do differently?")
    
    message = "\n".join(parts)
    
    create_notification(
        type="evening_review",
        title="Evening Reflection",
        message=message,
        priority="low"
    )
    
    return {
        "status": "success",
        "items_affected": len(completed_today),
        "summary": {
            "completed_today": len(completed_today),
            "still_active": active_count
        }
    }


def generate_weekly_review_reminder(params: Dict = None) -> Dict:
    """Generate weekly review reminder."""
    # Check if weekly review exists for this week
    from services.review_service import get_week_bounds
    week_start, week_end = get_week_bounds(0)
    
    existing = execute_query(
        "SELECT * FROM reviews WHERE week_start = ?", (week_start,)
    )
    
    if existing:
        return {
            "status": "success",
            "items_affected": 0,
            "message": "Weekly review already completed"
        }
    
    create_notification(
        type="weekly_review",
        title="Weekly Review Time",
        message="Take 10 minutes to review your week. What did you accomplish? What's coming up?",
        priority="medium"
    )
    
    return {
        "status": "success",
        "items_affected": 0,
        "notifications_sent": 1
    }


# Task handler registry
PROACTIVE_HANDLERS = {
    'morning_briefing': generate_morning_briefing,
    'evening_review': generate_evening_review,
    'weekly_review_reminder': generate_weekly_review_reminder,
    'proactive_check': run_proactive_check,
    'contact_check': run_contact_check,
    'pattern_analysis': run_pattern_analysis,
    'maintenance': run_maintenance
}


def get_handler(task_type: str):
    """Get handler for a proactive task type."""
    return PROACTIVE_HANDLERS.get(task_type)
