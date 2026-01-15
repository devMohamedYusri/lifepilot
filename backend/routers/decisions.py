"""Decisions router for decision journal lifecycle."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
import json

from models import (
    DecisionCreate, DecisionUpdate, DecisionOutcome, 
    DecisionResponse, DecisionInsights, DecisionStats, ItemResponse
)
from database import execute_query, execute_write
from services.decision_service import expand_decision, generate_insights

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.post("/{item_id}/expand", response_model=DecisionResponse)
async def expand_decision_item(item_id: int, decision: DecisionCreate = None):
    """Expand a decision-type item into a full decision record with AI analysis."""
    # Verify item exists and is a decision type
    items = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    if not items:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item = items[0]
    if item["type"] != "decision":
        raise HTTPException(status_code=400, detail="Item is not a decision type")
    
    # Check if decision record already exists
    existing = execute_query("SELECT * FROM decisions WHERE item_id = ?", (item_id,))
    if existing:
        return DecisionResponse(**existing[0])
    
    # Use AI to expand the decision
    ai_analysis = expand_decision(item["raw_content"])
    
    # Create decision record
    options_json = json.dumps(ai_analysis.get("options", []))
    stakeholders_json = json.dumps(ai_analysis.get("stakeholders", []))
    tags_json = json.dumps(ai_analysis.get("suggested_tags", []))
    
    query = """
        INSERT INTO decisions (
            item_id, situation, context, options, stakeholders, 
            deadline, tags, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'deliberating', ?, ?)
    """
    now = datetime.now().isoformat()
    params = (
        item_id,
        ai_analysis.get("situation"),
        ai_analysis.get("decision_question"),
        options_json,
        stakeholders_json,
        ai_analysis.get("suggested_deadline"),
        tags_json,
        now,
        now,
    )
    
    decision_id = execute_write(query, params)
    
    result = execute_query("SELECT * FROM decisions WHERE id = ?", (decision_id,))
    return DecisionResponse(**result[0])


@router.get("", response_model=List[DecisionResponse])
async def list_decisions(
    status: Optional[str] = Query(None, pattern="^(deliberating|decided|awaiting_outcome|completed)$"),
    tag: Optional[str] = Query(None),
    item_id: Optional[int] = Query(None)
):
    """List decisions with filters."""
    query = "SELECT d.*, i.raw_content as item_content FROM decisions d LEFT JOIN items i ON d.item_id = i.id WHERE 1=1"
    params = []
    
    if status:
        query += " AND d.status = ?"
        params.append(status)
    
    if tag:
        query += " AND d.tags LIKE ?"
        params.append(f"%{tag}%")
    
    if item_id:
        query += " AND d.item_id = ?"
        params.append(item_id)
    
    query += " ORDER BY d.updated_at DESC, d.created_at DESC"
    
    results = execute_query(query, tuple(params))
    decisions = []
    for row in results:
        row_dict = dict(row)
        row_dict.pop('item_content', None)
        decisions.append(DecisionResponse(**row_dict))
    return decisions


@router.get("/due-for-review", response_model=List[DecisionResponse])
async def get_due_for_review():
    """Get decisions that need outcome recording."""
    today = datetime.now().date().isoformat()
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    
    query = """
        SELECT * FROM decisions 
        WHERE status IN ('decided', 'awaiting_outcome')
        AND (
            expected_timeline <= ? 
            OR (expected_timeline IS NULL AND created_at <= ?)
        )
        ORDER BY expected_timeline ASC, created_at ASC
    """
    
    results = execute_query(query, (today, thirty_days_ago))
    return [DecisionResponse(**row) for row in results]


@router.get("/insights", response_model=DecisionInsights)
async def get_decision_insights(months: int = Query(6, ge=1, le=24)):
    """Get AI-generated insights from past decisions."""
    cutoff = (datetime.now() - timedelta(days=months * 30)).isoformat()
    
    decisions = execute_query(
        "SELECT * FROM decisions WHERE status = 'completed' AND created_at >= ? ORDER BY created_at DESC",
        (cutoff,)
    )
    
    ai_insights = generate_insights(decisions)
    return DecisionInsights(**ai_insights)


@router.get("/stats", response_model=DecisionStats)
async def get_decision_stats():
    """Get decision statistics."""
    all_decisions = execute_query("SELECT * FROM decisions")
    
    stats = {
        "total": len(all_decisions),
        "deliberating": 0,
        "decided": 0,
        "awaiting_outcome": 0,
        "completed": 0,
        "average_rating": None,
        "average_confidence": None,
        "by_tag": {}
    }
    
    ratings = []
    confidences = []
    
    for d in all_decisions:
        status = d.get("status") or "deliberating"
        if status in stats:
            stats[status] += 1
        
        if d.get("rating"):
            ratings.append(d["rating"])
        if d.get("confidence"):
            confidences.append(d["confidence"])
        
        # Count tags
        try:
            tags = json.loads(d.get("tags") or "[]")
            for tag in tags:
                stats["by_tag"][tag] = stats["by_tag"].get(tag, 0) + 1
        except:
            pass
    
    if ratings:
        stats["average_rating"] = sum(ratings) / len(ratings)
    if confidences:
        stats["average_confidence"] = sum(confidences) / len(confidences)
    
    return DecisionStats(**stats)


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(decision_id: int):
    """Get a specific decision with linked item."""
    results = execute_query("SELECT * FROM decisions WHERE id = ?", (decision_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    decision = dict(results[0])
    
    items = execute_query("SELECT * FROM items WHERE id = ?", (decision["item_id"],))
    if items:
        decision["item"] = ItemResponse(**items[0])
    
    return DecisionResponse(**decision)


@router.patch("/{decision_id}", response_model=DecisionResponse)
async def update_decision(decision_id: int, update: DecisionUpdate):
    """Update a decision. Auto-updates status based on fields filled."""
    results = execute_query("SELECT * FROM decisions WHERE id = ?", (decision_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    current = results[0]
    updates = ["updated_at = ?"]
    params = [datetime.now().isoformat()]
    
    # Handle each field
    field_map = {
        "situation": "situation",
        "options": "options",
        "stakeholders": "stakeholders", 
        "deadline": "deadline",
        "chosen_option": "chosen_option",
        "reasoning": "reasoning",
        "confidence": "confidence",
        "expected_outcome": "expected_outcome",
        "expected_timeline": "expected_timeline",
        "tags": "tags",
    }
    
    for model_field, db_field in field_map.items():
        value = getattr(update, model_field, None)
        if value is not None:
            updates.append(f"{db_field} = ?")
            params.append(value)
    
    # Auto-determine status based on what's filled
    new_status = current.get("status") or "deliberating"
    if update.chosen_option:
        new_status = "decided"
    if update.expected_outcome or update.expected_timeline:
        new_status = "awaiting_outcome"
    
    updates.append("status = ?")
    params.append(new_status)
    
    params.append(decision_id)
    query = f"UPDATE decisions SET {', '.join(updates)} WHERE id = ?"
    execute_write(query, tuple(params))
    
    results = execute_query("SELECT * FROM decisions WHERE id = ?", (decision_id,))
    return DecisionResponse(**results[0])


@router.post("/{decision_id}/record-outcome", response_model=DecisionResponse)
async def record_outcome(decision_id: int, outcome: DecisionOutcome):
    """Record the outcome of a decision."""
    results = execute_query("SELECT * FROM decisions WHERE id = ?", (decision_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    query = """
        UPDATE decisions SET 
            actual_outcome = ?,
            rating = ?,
            expectation_matched = ?,
            lessons = ?,
            would_change = ?,
            outcome_date = ?,
            status = 'completed',
            updated_at = ?
        WHERE id = ?
    """
    now = datetime.now().isoformat()
    execute_write(query, (
        outcome.actual_outcome,
        outcome.outcome_rating,
        outcome.expectation_matched,
        outcome.lessons,
        outcome.would_change,
        now,
        now,
        decision_id
    ))
    
    results = execute_query("SELECT * FROM decisions WHERE id = ?", (decision_id,))
    return DecisionResponse(**results[0])
