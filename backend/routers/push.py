"""API router for push notification endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from services.push_service import (
    get_vapid_public_key, is_push_configured,
    save_subscription, get_all_subscriptions, delete_subscription,
    get_push_preferences, update_push_preferences,
    send_notification_to_all
)

router = APIRouter(prefix="/api/push", tags=["push"])


# === Models ===

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]  # {p256dh, auth}
    device_name: Optional[str] = None


class PushPreferencesUpdate(BaseModel):
    task_reminders: Optional[bool] = None
    followup_reminders: Optional[bool] = None
    contact_reminders: Optional[bool] = None
    daily_summary: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class TestNotification(BaseModel):
    title: str = "Test Notification"
    body: str = "This is a test notification from LifePilot"


# === Status ===

@router.get("/status")
async def get_push_status():
    """Get push notification configuration status."""
    configured = is_push_configured()
    subscriptions = get_all_subscriptions(enabled_only=True)
    
    return {
        "configured": configured,
        "vapid_public_key": get_vapid_public_key() if configured else None,
        "subscription_count": len(subscriptions),
        "message": "VAPID keys required" if not configured else "Ready"
    }


# === VAPID Public Key ===

@router.get("/vapid-key")
async def get_vapid_key():
    """Get the VAPID public key for client subscription."""
    key = get_vapid_public_key()
    if not key:
        raise HTTPException(
            status_code=503, 
            detail="Push notifications not configured. Set VAPID_PUBLIC_KEY environment variable."
        )
    return {"publicKey": key}


# === Subscriptions ===

@router.post("/subscribe")
async def subscribe(subscription: PushSubscription, user_agent: str = None):
    """
    Subscribe to push notifications.
    
    The subscription object contains:
    - endpoint: Push service URL
    - keys.p256dh: Public key for encryption
    - keys.auth: Authentication secret
    """
    if not subscription.keys.get('p256dh') or not subscription.keys.get('auth'):
        raise HTTPException(status_code=400, detail="Missing encryption keys")
    
    result = save_subscription(
        endpoint=subscription.endpoint,
        p256dh_key=subscription.keys['p256dh'],
        auth_key=subscription.keys['auth'],
        device_name=subscription.device_name,
        user_agent=user_agent
    )
    
    return {
        "success": True,
        "subscription_id": result['id'],
        "message": "Subscription updated" if result.get('updated') else "Subscription created"
    }


@router.delete("/unsubscribe")
async def unsubscribe(endpoint: str):
    """Unsubscribe from push notifications."""
    delete_subscription(endpoint)
    return {"success": True, "message": "Unsubscribed"}


@router.get("/subscriptions")
async def list_subscriptions():
    """List all push subscriptions (admin)."""
    subs = get_all_subscriptions(enabled_only=False)
    return [
        {
            "id": s['id'],
            "device_name": s.get('device_name'),
            "enabled": bool(s.get('enabled', 1)),
            "created_at": s.get('created_at'),
            "last_used_at": s.get('last_used_at')
        }
        for s in subs
    ]


# === Preferences ===

@router.get("/preferences")
async def get_preferences():
    """Get push notification preferences."""
    prefs = get_push_preferences()
    return prefs


@router.patch("/preferences")
async def update_preferences(updates: PushPreferencesUpdate):
    """Update push notification preferences."""
    update_dict = updates.model_dump(exclude_unset=True)
    update_push_preferences(update_dict)
    return {"success": True}


# === Test ===

@router.post("/test")
async def send_test_notification(notification: TestNotification):
    """Send a test notification to all subscribed devices."""
    if not is_push_configured():
        raise HTTPException(
            status_code=503,
            detail="Push notifications not configured"
        )
    
    count = await send_notification_to_all(
        title=notification.title,
        body=notification.body,
        data={"url": "/", "test": True}
    )
    
    return {
        "success": True,
        "sent_count": count,
        "message": f"Sent to {count} device(s)"
    }
