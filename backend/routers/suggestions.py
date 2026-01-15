"""API router for proactive suggestions endpoints."""
from fastapi import APIRouter, HTTPException
from typing import List
from models import (
    SuggestionResponse, SuggestionResponseRecord,
    SuggestionPreferences, SuggestionStats, SuggestionGenerateResult
)
from services.suggestion_service import (
    get_pending_suggestions,
    generate_suggestions,
    record_response,
    mark_shown,
    get_preferences,
    update_preferences,
    get_stats
)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


@router.get("", response_model=List[SuggestionResponse])
async def list_suggestions(limit: int = 5):
    """
    Get current pending suggestions ready to display.
    Automatically marks them as shown.
    """
    suggestions = get_pending_suggestions(limit=limit)
    
    # Mark each as shown
    for s in suggestions:
        mark_shown(s['id'])
    
    return [SuggestionResponse(**s) for s in suggestions]


@router.post("/generate", response_model=SuggestionGenerateResult)
async def trigger_generation(force: bool = False):
    """
    Trigger suggestion generation based on current context.
    
    Set force=True to bypass quiet hours and fatigue limits.
    """
    result = generate_suggestions(force=force)
    
    # Convert suggestions to response models if present
    suggestions = []
    if result.get('suggestions'):
        for s in result['suggestions']:
            # Fetch full suggestion data
            from database import execute_query
            full = execute_query("SELECT * FROM suggestions WHERE id = ?", (s['id'],))
            if full:
                suggestions.append(SuggestionResponse(**dict(full[0])))
    
    return SuggestionGenerateResult(
        generated=result.get('generated', 0),
        suggestions=suggestions
    )


@router.post("/{suggestion_id}/response")
async def record_suggestion_response(suggestion_id: int, response: SuggestionResponseRecord):
    """
    Record user response to a suggestion (acted or dismissed).
    This updates effectiveness metrics.
    """
    record_response(suggestion_id, response.response_type.value)
    return {"success": True, "suggestion_id": suggestion_id}


@router.get("/preferences", response_model=SuggestionPreferences)
async def get_user_preferences():
    """
    Get user's suggestion preferences.
    """
    prefs = get_preferences()
    return SuggestionPreferences(**prefs)


@router.patch("/preferences")
async def update_user_preferences(preferences: SuggestionPreferences):
    """
    Update user's suggestion preferences.
    """
    update_preferences(preferences.model_dump())
    return {"success": True}


@router.get("/stats", response_model=List[SuggestionStats])
async def get_suggestion_stats():
    """
    Get effectiveness statistics for suggestion types.
    Sorted by effectiveness score descending.
    """
    stats = get_stats()
    return [SuggestionStats(**s) for s in stats]
