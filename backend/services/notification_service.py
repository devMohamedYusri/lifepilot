"""Notification service for smart proactive notifications."""
import json
import re
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .groq_service import call_groq
from database import execute_query, execute_write


def get_pending_notifications() -> List[Dict]:
    """Get all pending notifications ready to show."""
    now = datetime.now().isoformat()
    
    notifications = execute_query("""
        SELECT * FROM notifications 
        WHERE status = 'pending'
        AND scheduled_for <= ?
        AND (expires_at IS NULL OR expires_at > ?)
        ORDER BY 
            CASE priority 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                ELSE 3 
            END,
            scheduled_for ASC
    """, (now, now))
    
    return [dict(n) for n in notifications]


def create_notification(
    type: str,
    title: str,
    message: str = None,
    priority: str = "medium",
    linked_type: str = None,
    linked_id: int = None,
    scheduled_for: str = None
) -> int:
    """Create a new notification."""
    if not scheduled_for:
        scheduled_for = datetime.now().isoformat()
    
    query = """
        INSERT INTO notifications (type, title, message, priority, linked_type, linked_id, scheduled_for, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """
    
    return execute_write(query, (
        type, title, message, priority, linked_type, linked_id, scheduled_for, datetime.now().isoformat()
    ))


NOTIFICATION_PROMPT = """Determine what notifications to create based on current state. Return ONLY valid JSON.

Current time: {now}
Today: {today}

Current state:
- Overdue tasks: {overdue_count}
- Follow-ups needed: {followups_count}
- Contacts overdue: {contacts_count}
- Upcoming birthdays: {birthdays_count}
- Last energy log: {last_energy_log}

Generate appropriate notifications. Be helpful but not annoying. Prioritize what truly matters.

Return format:
{{
  "notifications": [
    {{
      "type": "task_due",
      "title": "Overdue task reminder",
      "message": "You have {overdue_count} overdue items",
      "priority": "high"
    }}
  ],
  "daily_summary": "Summary of what needs attention"
}}"""


def generate_smart_notifications() -> Dict[str, Any]:
    """AI determines what notifications to create."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    
    # Gather current state
    overdue_tasks = execute_query(
        "SELECT COUNT(*) as count FROM items WHERE due_date < ? AND status != 'done'",
        (today,)
    )
    overdue_count = overdue_tasks[0]['count'] if overdue_tasks else 0
    
    followups = execute_query(
        "SELECT COUNT(*) as count FROM items WHERE type = 'waiting_for' AND follow_up_date <= ? AND status != 'done'",
        (today,)
    )
    followups_count = followups[0]['count'] if followups else 0
    
    contacts_overdue = execute_query(
        "SELECT COUNT(*) as count FROM contacts WHERE is_active = 1 AND next_contact_date <= ?",
        (today,)
    )
    contacts_count = contacts_overdue[0]['count'] if contacts_overdue else 0
    
    # Get upcoming birthdays (next 7 days)
    birthdays_count = 0  # Would require parsing MM-DD format
    
    last_energy = execute_query(
        "SELECT * FROM energy_logs ORDER BY logged_at DESC LIMIT 1"
    )
    last_energy_log = last_energy[0]['logged_at'] if last_energy else "Never"
    
    # Check if we already have pending notifications to avoid duplicates
    existing = execute_query(
        "SELECT COUNT(*) as count FROM notifications WHERE status = 'pending'"
    )
    if existing and existing[0]['count'] > 5:
        return {"created": 0, "message": "Already have pending notifications"}
    
    notifications_created = []
    
    # Create notifications based on state
    if overdue_count > 0:
        # Check if we already have a task_due notification
        existing_task = execute_query(
            "SELECT id FROM notifications WHERE type = 'task_due' AND status = 'pending' LIMIT 1"
        )
        if not existing_task:
            create_notification(
                type="task_due",
                title=f"{overdue_count} overdue task{'s' if overdue_count > 1 else ''}",
                message="Time to tackle these!",
                priority="high" if overdue_count > 2 else "medium",
                linked_type="items"
            )
            notifications_created.append("task_due")
    
    if followups_count > 0:
        existing_followup = execute_query(
            "SELECT id FROM notifications WHERE type = 'follow_up' AND status = 'pending' LIMIT 1"
        )
        if not existing_followup:
            create_notification(
                type="follow_up",
                title=f"{followups_count} follow-up{'s' if followups_count > 1 else ''} needed",
                message="Check in on items you're waiting for",
                priority="medium",
                linked_type="items"
            )
            notifications_created.append("follow_up")
    
    if contacts_count > 0:
        existing_contact = execute_query(
            "SELECT id FROM notifications WHERE type = 'contact' AND status = 'pending' LIMIT 1"
        )
        if not existing_contact:
            create_notification(
                type="contact",
                title=f"{contacts_count} contact{'s' if contacts_count > 1 else ''} to reach out to",
                message="Stay connected with your people",
                priority="low",
                linked_type="contacts"
            )
            notifications_created.append("contact")
    
    # Energy check reminder (if no log in 4+ hours during work hours)
    if last_energy_log == "Never" or (8 <= now.hour <= 18):
        try:
            if last_energy_log != "Never":
                last_time = datetime.fromisoformat(last_energy_log.replace('Z', '+00:00'))
                hours_ago = (now - last_time.replace(tzinfo=None)).total_seconds() / 3600
                if hours_ago >= 4:
                    existing_energy = execute_query(
                        "SELECT id FROM notifications WHERE type = 'energy_check' AND status = 'pending' LIMIT 1"
                    )
                    if not existing_energy:
                        create_notification(
                            type="energy_check",
                            title="How's your energy?",
                            message="Quick check-in to track your patterns",
                            priority="low"
                        )
                        notifications_created.append("energy_check")
        except:
            pass
    
    return {
        "created": len(notifications_created),
        "types": notifications_created,
        "state": {
            "overdue_tasks": overdue_count,
            "followups": followups_count,
            "contacts": contacts_count
        }
    }


def get_daily_digest() -> Dict[str, Any]:
    """Generate a daily digest summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Tasks due today
    tasks_due = execute_query(
        "SELECT * FROM items WHERE due_date = ? AND status != 'done'",
        (today,)
    )
    
    # Overdue
    overdue = execute_query(
        "SELECT * FROM items WHERE due_date < ? AND status != 'done'",
        (today,)
    )
    
    # Follow-ups
    followups = execute_query(
        "SELECT * FROM items WHERE type = 'waiting_for' AND follow_up_date <= ? AND status != 'done'",
        (today,)
    )
    
    # Contacts needing attention
    contacts = execute_query(
        "SELECT * FROM contacts WHERE is_active = 1 AND next_contact_date <= ?",
        (today,)
    )
    
    return {
        "date": today,
        "tasks_due_today": len(tasks_due),
        "overdue_count": len(overdue),
        "followups_needed": len(followups),
        "contacts_to_reach": len(contacts),
        "summary": f"You have {len(tasks_due)} tasks due today, {len(overdue)} overdue, and {len(followups)} follow-ups pending."
    }
