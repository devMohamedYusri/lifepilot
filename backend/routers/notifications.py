"""Notifications router for smart proactive notifications."""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime

from database import execute_query, execute_write
from services.notification_service import (
    get_pending_notifications, create_notification,
    generate_smart_notifications, get_daily_digest
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/pending")
async def list_pending():
    """Get all pending notifications ready to show."""
    return get_pending_notifications()


@router.post("/{notification_id}/dismiss")
async def dismiss_notification(notification_id: int):
    """Dismiss a notification."""
    existing = execute_query("SELECT * FROM notifications WHERE id = ?", (notification_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    execute_write(
        "UPDATE notifications SET status = 'dismissed', shown_at = ? WHERE id = ?",
        (datetime.now().isoformat(), notification_id)
    )
    
    return {"message": "Notification dismissed", "id": notification_id}


@router.post("/{notification_id}/act")
async def act_on_notification(notification_id: int):
    """Mark notification as acted upon and return linked item."""
    existing = execute_query("SELECT * FROM notifications WHERE id = ?", (notification_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification = dict(existing[0])
    
    execute_write(
        "UPDATE notifications SET status = 'acted', acted_at = ? WHERE id = ?",
        (datetime.now().isoformat(), notification_id)
    )
    
    # Return linked item info for navigation
    linked_type = notification.get('linked_type')
    linked_id = notification.get('linked_id')
    
    linked_item = None
    if linked_type and linked_id:
        if linked_type == 'item' or linked_type == 'items':
            items = execute_query("SELECT * FROM items WHERE id = ?", (linked_id,))
            if items:
                linked_item = dict(items[0])
        elif linked_type == 'contact' or linked_type == 'contacts':
            contacts = execute_query("SELECT * FROM contacts WHERE id = ?", (linked_id,))
            if contacts:
                linked_item = dict(contacts[0])
    
    return {
        "message": "Notification acted upon",
        "id": notification_id,
        "linked_type": linked_type,
        "linked_id": linked_id,
        "linked_item": linked_item
    }


@router.get("/generate")
async def generate_notifications():
    """Generate smart notifications based on current state."""
    result = generate_smart_notifications()
    return result


@router.get("/digest")
async def daily_digest():
    """Get daily digest summary."""
    return get_daily_digest()


@router.get("/settings")
async def get_settings():
    """Get all notification settings."""
    settings = execute_query("SELECT * FROM notification_settings")
    return [dict(s) for s in settings]


@router.patch("/settings/{notification_type}")
async def update_settings(notification_type: str, updates: dict):
    """Update settings for a notification type."""
    # Check if setting exists
    existing = execute_query("SELECT * FROM notification_settings WHERE type = ?", (notification_type,))
    
    if not existing:
        # Create new setting
        execute_write(
            "INSERT INTO notification_settings (type, enabled, frequency, quiet_hours_start, quiet_hours_end, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                notification_type,
                updates.get('enabled', 1),
                updates.get('frequency'),
                updates.get('quiet_hours_start'),
                updates.get('quiet_hours_end'),
                datetime.now().isoformat()
            )
        )
    else:
        # Update existing
        allowed_fields = ['enabled', 'frequency', 'quiet_hours_start', 'quiet_hours_end']
        set_clauses = []
        params = []
        
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = ?")
                params.append(updates[field])
        
        if set_clauses:
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(notification_type)
            
            execute_write(
                f"UPDATE notification_settings SET {', '.join(set_clauses)} WHERE type = ?",
                tuple(params)
            )
    
    result = execute_query("SELECT * FROM notification_settings WHERE type = ?", (notification_type,))
    return dict(result[0]) if result else {"type": notification_type}


@router.post("/clear-all")
async def clear_all():
    """Clear all pending notifications."""
    execute_write(
        "UPDATE notifications SET status = 'dismissed', shown_at = ? WHERE status = 'pending'",
        (datetime.now().isoformat(),)
    )
    return {"message": "All notifications cleared"}


@router.get("/count")
async def get_count():
    """Get count of pending notifications."""
    result = execute_query(
        "SELECT COUNT(*) as count FROM notifications WHERE status = 'pending'"
    )
    high_priority = execute_query(
        "SELECT COUNT(*) as count FROM notifications WHERE status = 'pending' AND priority = 'high'"
    )
    
    return {
        "total": result[0]['count'] if result else 0,
        "high_priority": high_priority[0]['count'] if high_priority else 0
    }
