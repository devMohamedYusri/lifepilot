"""API router for calendar integration endpoints."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import List, Optional
from datetime import datetime
from models import (
    CalendarConnectionResponse, CalendarEventResponse,
    SyncLogResponse, FreeBlockResponse, CalendarPreferences,
    SyncResult, CalendarEventCreate
)
from services.calendar_service import (
    get_auth_url, complete_oauth, get_connections, delete_connection,
    get_preferences, update_preferences, get_connection
)
from services.calendar_sync_service import (
    sync_import, sync_export, run_full_sync, get_events, get_sync_logs
)
from services.free_time_service import (
    get_free_blocks, suggest_focus_time, check_availability, get_day_summary
)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


# =====================================================
# OAuth Endpoints
# =====================================================

@router.get("/auth/{provider}")
async def initiate_oauth(provider: str):
    """
    Initiate OAuth flow for a calendar provider.
    Returns the authorization URL to redirect the user to.
    """
    try:
        result = get_auth_url(provider)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback/{provider}")
async def oauth_callback(provider: str, code: str, state: str):
    """
    Handle OAuth callback from provider.
    Exchanges code for tokens and creates connection.
    """
    try:
        result = complete_oauth(provider, code, state)
        # Redirect to frontend settings page with success
        return RedirectResponse(
            url=f"http://localhost:5173?calendar_connected=true&email={result['email']}",
            status_code=302
        )
    except ValueError as e:
        # Redirect with error
        return RedirectResponse(
            url=f"http://localhost:5173?calendar_error={str(e)}",
            status_code=302
        )


# =====================================================
# Connection Management
# =====================================================

@router.get("/connections", response_model=List[CalendarConnectionResponse])
async def list_connections():
    """Get all calendar connections."""
    connections = get_connections()
    return [CalendarConnectionResponse(**c) for c in connections]


@router.delete("/connections/{connection_id}")
async def remove_connection(connection_id: int):
    """Delete a calendar connection and its data."""
    conn = get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    delete_connection(connection_id)
    return {"success": True, "message": "Connection removed"}


# =====================================================
# Sync Operations
# =====================================================

@router.post("/sync/{connection_id}")
async def trigger_sync(
    connection_id: int,
    direction: str = Query("bidirectional", regex="^(import|export|bidirectional)$")
):
    """
    Trigger calendar sync for a connection.
    Direction can be: import, export, or bidirectional
    """
    conn = get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    if direction == "import":
        result = sync_import(connection_id)
    elif direction == "export":
        result = sync_export(connection_id)
    else:
        result = run_full_sync(connection_id)
    
    return result


@router.get("/sync/{connection_id}/logs", response_model=List[SyncLogResponse])
async def list_sync_logs(connection_id: int, limit: int = 10):
    """Get sync history for a connection."""
    logs = get_sync_logs(connection_id, limit)
    return [SyncLogResponse(**l) for l in logs]


# =====================================================
# Calendar Events
# =====================================================

@router.get("/events", response_model=List[CalendarEventResponse])
async def list_events(
    connection_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get calendar events.
    Can filter by connection and date range.
    """
    events = get_events(connection_id, start_date, end_date)
    return [CalendarEventResponse(**e) for e in events]


# =====================================================
# Free Time Analysis
# =====================================================

@router.get("/free-blocks", response_model=List[FreeBlockResponse])
async def list_free_blocks(
    date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
    min_duration: Optional[int] = None
):
    """
    Get free time blocks for a date.
    Returns gaps between calendar events during working hours.
    """
    blocks = get_free_blocks(date, min_duration)
    return [FreeBlockResponse(**b) for b in blocks]


@router.get("/focus-suggestion")
async def get_focus_suggestion(
    date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
    duration: int = 90
):
    """
    Get suggested focus time for a date.
    Considers free blocks and energy patterns.
    """
    suggestion = suggest_focus_time(date, duration)
    if not suggestion:
        return {"available": False, "message": "No suitable focus time found"}
    return suggestion


@router.get("/availability")
async def check_time_availability(start_time: str, end_time: str):
    """
    Check if a time slot is available.
    Returns availability status and any conflicts.
    """
    return check_availability(start_time, end_time)


@router.get("/day-summary")
async def get_day_schedule_summary(
    date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    Get a summary of the day's schedule.
    Includes events, busy/free hours, and focus suggestions.
    """
    return get_day_summary(date)


# =====================================================
# Preferences
# =====================================================

@router.get("/preferences", response_model=CalendarPreferences)
async def get_calendar_preferences():
    """Get calendar sync preferences."""
    prefs = get_preferences()
    return CalendarPreferences(**prefs)


@router.patch("/preferences")
async def update_calendar_preferences(preferences: CalendarPreferences):
    """Update calendar sync preferences."""
    update_preferences(preferences.model_dump())
    return {"success": True}
