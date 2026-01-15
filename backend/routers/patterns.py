"""API router for pattern recognition endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from models import (
    PatternResponse, InsightResponse, PatternFeedbackCreate,
    PatternFeedbackResponse, AnalysisRequest, AnalysisResult, PatternDashboard
)
from services.pattern_service import (
    run_full_analysis,
    get_all_patterns,
    get_pattern_by_id,
    get_active_insights,
    submit_feedback,
    get_dashboard_stats
)
from database import execute_write

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.post("/analyze", response_model=AnalysisResult)
async def trigger_analysis(request: AnalysisRequest = None):
    """
    Trigger pattern analysis across all user data.
    
    This is computationally expensive and should be called on-demand.
    Results are cached in the database.
    """
    if request is None:
        request = AnalysisRequest()
    
    result = run_full_analysis(
        scope=request.scope,
        date_range_days=request.date_range_days or 30
    )
    
    return AnalysisResult(**result)


@router.get("", response_model=List[PatternResponse])
async def list_patterns(
    pattern_type: Optional[str] = Query(None, description="Filter by type: temporal, behavioral, correlation, anomaly"),
    category: Optional[str] = Query(None, description="Filter by category: productivity, energy, social, learning, decisions"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    active_only: bool = Query(True, description="Only return active patterns")
):
    """
    Get all discovered patterns with optional filters.
    """
    patterns = get_all_patterns(
        pattern_type=pattern_type,
        category=category,
        min_confidence=min_confidence,
        active_only=active_only
    )
    
    return [PatternResponse(**p) for p in patterns]


@router.get("/insights", response_model=List[InsightResponse])
async def list_insights():
    """
    Get active insights that haven't been dismissed.
    Ordered by priority and recency.
    """
    insights = get_active_insights()
    return [InsightResponse(**i) for i in insights]


@router.get("/dashboard", response_model=PatternDashboard)
async def get_dashboard():
    """
    Get aggregate statistics for the pattern dashboard.
    """
    stats = get_dashboard_stats()
    return PatternDashboard(**stats)


@router.get("/{pattern_id}", response_model=PatternResponse)
async def get_pattern(pattern_id: int):
    """
    Get detailed information about a specific pattern.
    """
    pattern = get_pattern_by_id(pattern_id)
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    # Increment times_shown
    execute_write(
        "UPDATE patterns SET times_shown = times_shown + 1 WHERE id = ?",
        (pattern_id,)
    )
    
    return PatternResponse(**pattern)


@router.post("/{pattern_id}/feedback", response_model=PatternFeedbackResponse)
async def submit_pattern_feedback(pattern_id: int, feedback: PatternFeedbackCreate):
    """
    Submit feedback on a pattern's accuracy or helpfulness.
    This adjusts the pattern's confidence score.
    """
    # Verify pattern exists
    pattern = get_pattern_by_id(pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    feedback_id = submit_feedback(
        pattern_id=pattern_id,
        feedback_type=feedback.feedback_type.value,
        comment=feedback.comment
    )
    
    from database import execute_query
    from datetime import datetime
    
    return PatternFeedbackResponse(
        id=feedback_id,
        pattern_id=pattern_id,
        feedback_type=feedback.feedback_type,
        comment=feedback.comment,
        created_at=datetime.now().isoformat()
    )


@router.post("/insights/{insight_id}/dismiss")
async def dismiss_insight(insight_id: int):
    """
    Dismiss an insight so it no longer appears in active insights.
    """
    execute_write(
        "UPDATE insights SET status = 'dismissed' WHERE id = ?",
        (insight_id,)
    )
    return {"success": True, "insight_id": insight_id}


@router.post("/insights/{insight_id}/act")
async def mark_insight_acted(insight_id: int):
    """
    Mark an insight as acted upon.
    """
    execute_write(
        "UPDATE insights SET status = 'acted' WHERE id = ?",
        (insight_id,)
    )
    return {"success": True, "insight_id": insight_id}
