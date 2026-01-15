"""Push notification service for web push notifications."""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, time

from database import execute_query, execute_write

logger = logging.getLogger(__name__)

# VAPID keys for web push (generate these for production)
# Use: from py_vapid import Vapid; v = Vapid(); v.generate_keys()
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_EMAIL = os.getenv('VAPID_EMAIL', 'mailto:admin@lifepilot.local')


def get_vapid_public_key() -> str:
    """Get the VAPID public key for client subscription."""
    return VAPID_PUBLIC_KEY


def is_push_configured() -> bool:
    """Check if VAPID keys are configured."""
    return bool(VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY)


# === Subscription Management ===

def save_subscription(
    endpoint: str,
    p256dh_key: str,
    auth_key: str,
    device_name: str = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """
    Save a push subscription.
    
    Args:
        endpoint: Push service endpoint URL
        p256dh_key: P-256 Diffie-Hellman public key
        auth_key: Authentication secret
        device_name: Optional device name
        user_agent: Browser user agent
        
    Returns:
        Subscription record
    """
    now = datetime.now().isoformat()
    
    # Check if subscription exists
    existing = execute_query(
        "SELECT id FROM push_subscriptions WHERE endpoint = ?",
        (endpoint,)
    )
    
    if existing:
        # Update existing
        execute_write("""
            UPDATE push_subscriptions 
            SET p256dh_key = ?, auth_key = ?, device_name = ?, 
                user_agent = ?, enabled = 1, last_used_at = ?
            WHERE endpoint = ?
        """, (p256dh_key, auth_key, device_name, user_agent, now, endpoint))
        
        return {"id": existing[0]['id'], "updated": True}
    else:
        # Create new
        sub_id = execute_write("""
            INSERT INTO push_subscriptions 
            (endpoint, p256dh_key, auth_key, device_name, user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (endpoint, p256dh_key, auth_key, device_name, user_agent, now))
        
        return {"id": sub_id, "created": True}


def get_all_subscriptions(enabled_only: bool = True) -> List[Dict[str, Any]]:
    """Get all push subscriptions."""
    query = "SELECT * FROM push_subscriptions"
    if enabled_only:
        query += " WHERE enabled = 1"
    
    return execute_query(query)


def delete_subscription(endpoint: str) -> bool:
    """Delete a subscription by endpoint."""
    execute_write("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
    return True


def disable_subscription(endpoint: str) -> bool:
    """Disable a subscription (keep for re-enable)."""
    execute_write(
        "UPDATE push_subscriptions SET enabled = 0 WHERE endpoint = ?",
        (endpoint,)
    )
    return True


# === Preferences ===

def get_push_preferences() -> Dict[str, Any]:
    """Get push notification preferences."""
    prefs = execute_query("SELECT key, value FROM push_preferences")
    result = {}
    for p in prefs:
        value = p['value']
        if value in ('true', 'false'):
            value = value == 'true'
        result[p['key']] = value
    return result


def update_push_preferences(updates: Dict[str, Any]) -> bool:
    """Update push notification preferences."""
    now = datetime.now().isoformat()
    
    for key, value in updates.items():
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        
        execute_write("""
            INSERT OR REPLACE INTO push_preferences (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, str(value), now))
    
    return True


def is_quiet_hours() -> bool:
    """Check if current time is within quiet hours."""
    prefs = get_push_preferences()
    
    start_str = prefs.get('quiet_hours_start', '22:00')
    end_str = prefs.get('quiet_hours_end', '08:00')
    
    try:
        start = datetime.strptime(start_str, '%H:%M').time()
        end = datetime.strptime(end_str, '%H:%M').time()
        now = datetime.now().time()
        
        if start <= end:
            # Simple case: quiet hours don't span midnight
            return start <= now <= end
        else:
            # Quiet hours span midnight (e.g., 22:00 - 08:00)
            return now >= start or now <= end
    except:
        return False


# === Send Notifications ===

async def send_push_notification(
    subscription: Dict[str, Any],
    title: str,
    body: str,
    data: Dict[str, Any] = None,
    actions: List[Dict[str, str]] = None
) -> bool:
    """
    Send a push notification to a single subscription.
    
    Note: Requires pywebpush library for production use.
    This is a placeholder that logs the notification.
    
    Args:
        subscription: Subscription record from database
        title: Notification title
        body: Notification body text
        data: Additional data to include
        actions: Action buttons
        
    Returns:
        True if sent successfully
    """
    try:
        if not is_push_configured():
            logger.warning("VAPID keys not configured, skipping push notification")
            return False
        
        # Check quiet hours
        if is_quiet_hours():
            logger.info(f"Notification skipped (quiet hours): {title}")
            return False
        
        payload = {
            "title": title,
            "body": body,
            "data": data or {},
            "actions": actions or []
        }
        
        # In production, use pywebpush:
        # from pywebpush import webpush, WebPushException
        # webpush(
        #     subscription_info={
        #         "endpoint": subscription['endpoint'],
        #         "keys": {
        #             "p256dh": subscription['p256dh_key'],
        #             "auth": subscription['auth_key']
        #         }
        #     },
        #     data=json.dumps(payload),
        #     vapid_private_key=VAPID_PRIVATE_KEY,
        #     vapid_claims={"sub": VAPID_EMAIL}
        # )
        
        logger.info(f"Push notification sent: {title} -> {subscription.get('device_name', 'unknown device')}")
        
        # Update last_used_at
        execute_write(
            "UPDATE push_subscriptions SET last_used_at = ? WHERE id = ?",
            (datetime.now().isoformat(), subscription['id'])
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


async def send_notification_to_all(
    title: str,
    body: str,
    data: Dict[str, Any] = None,
    actions: List[Dict[str, str]] = None,
    notification_type: str = None
) -> int:
    """
    Send notification to all enabled subscriptions.
    
    Args:
        title: Notification title
        body: Notification body
        data: Additional data
        actions: Action buttons
        notification_type: Type for preference checking (task_reminders, etc.)
        
    Returns:
        Number of notifications sent
    """
    # Check preference for this notification type
    if notification_type:
        prefs = get_push_preferences()
        if not prefs.get(notification_type, True):
            logger.info(f"Notification type '{notification_type}' disabled by preferences")
            return 0
    
    subscriptions = get_all_subscriptions(enabled_only=True)
    sent = 0
    
    for sub in subscriptions:
        if await send_push_notification(sub, title, body, data, actions):
            sent += 1
    
    return sent


# === Notification Triggers ===

async def notify_task_due(item: Dict[str, Any]) -> bool:
    """Send notification for a task that's due."""
    return await send_notification_to_all(
        title="Task Due",
        body=item.get('ai_summary') or item.get('raw_content', 'A task is due'),
        data={"url": "/", "item_id": item.get('id')},
        actions=[
            {"action": "complete", "title": "Mark Done"},
            {"action": "snooze", "title": "Snooze"}
        ],
        notification_type="task_reminders"
    ) > 0


async def notify_followup_needed(item: Dict[str, Any]) -> bool:
    """Send notification for items needing follow-up."""
    person = item.get('person_involved', 'Someone')
    return await send_notification_to_all(
        title=f"Follow Up: {person}",
        body=item.get('ai_summary') or item.get('raw_content', 'Time to follow up'),
        data={"url": "/", "item_id": item.get('id')},
        actions=[
            {"action": "followup", "title": "Record Follow-up"},
            {"action": "dismiss", "title": "Dismiss"}
        ],
        notification_type="followup_reminders"
    ) > 0


async def notify_contact_reachout(contact: Dict[str, Any]) -> bool:
    """Send notification to reach out to a contact."""
    return await send_notification_to_all(
        title=f"Reach out to {contact.get('name')}",
        body=f"It's been a while since you connected with {contact.get('name')}",
        data={"url": "/people", "contact_id": contact.get('id')},
        notification_type="contact_reminders"
    ) > 0
