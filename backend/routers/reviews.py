"""Reviews router for weekly review system."""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from datetime import datetime
import json

from database import execute_query, execute_write
from services.review_service import generate_review, get_week_bounds

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/generate")
async def generate_weekly_review(offset_weeks: int = 0):
    """Generate a weekly review for the specified week."""
    review_data = generate_review(offset_weeks)
    
    # If new, save to database
    if review_data.get("is_new"):
        query = """
            INSERT INTO reviews (
                week_start, week_end, items_completed, bookmarks_read,
                decisions_made, follow_ups, accomplishments, themes,
                insights, encouragement, reflection_prompts, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            review_data["week_start"],
            review_data["week_end"],
            review_data["items_completed"],
            review_data["bookmarks_read"],
            review_data["decisions_made"],
            review_data["follow_ups"],
            json.dumps(review_data.get("accomplishments", [])),
            json.dumps(review_data.get("themes", [])),
            review_data.get("insights", ""),
            review_data.get("encouragement", ""),
            json.dumps(review_data.get("reflection_prompts", [])),
            datetime.now().isoformat()
        )
        review_id = execute_write(query, params)
        review_data["id"] = review_id
    
    return review_data


@router.get("")
async def list_reviews(limit: int = 10):
    """List past weekly reviews."""
    reviews = execute_query(
        "SELECT * FROM reviews ORDER BY week_start DESC LIMIT ?",
        (limit,)
    )
    
    result = []
    for r in reviews:
        review = dict(r)
        # Parse JSON fields
        try:
            review["accomplishments"] = json.loads(review.get("accomplishments") or "[]")
            review["themes"] = json.loads(review.get("themes") or "[]")
            review["reflection_prompts"] = json.loads(review.get("reflection_prompts") or "[]")
        except:
            pass
        result.append(review)
    
    return result


@router.get("/current")
async def get_current_week():
    """Get the current week's review if it exists."""
    week_start, week_end = get_week_bounds(0)
    
    existing = execute_query(
        "SELECT * FROM reviews WHERE week_start = ?", (week_start,)
    )
    
    if existing:
        review = dict(existing[0])
        try:
            review["accomplishments"] = json.loads(review.get("accomplishments") or "[]")
            review["themes"] = json.loads(review.get("themes") or "[]")
            review["reflection_prompts"] = json.loads(review.get("reflection_prompts") or "[]")
        except:
            pass
        return review
    
    return {"exists": False, "week_start": week_start, "week_end": week_end}


@router.patch("/{review_id}")
async def save_reflection(review_id: int, reflection: dict):
    """Save user reflection notes to a review."""
    existing = execute_query(
        "SELECT * FROM reviews WHERE id = ?", (review_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")
    
    updates = []
    params = []
    
    for field in ["reflection_notes", "wins", "challenges", "next_week_focus"]:
        if field in reflection:
            updates.append(f"{field} = ?")
            params.append(reflection[field])
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(review_id)
    query = f"UPDATE reviews SET {', '.join(updates)} WHERE id = ?"
    execute_write(query, tuple(params))
    
    # Return updated review
    result = execute_query("SELECT * FROM reviews WHERE id = ?", (review_id,))
    review = dict(result[0])
    try:
        review["accomplishments"] = json.loads(review.get("accomplishments") or "[]")
        review["themes"] = json.loads(review.get("themes") or "[]")
        review["reflection_prompts"] = json.loads(review.get("reflection_prompts") or "[]")
    except:
        pass
    return review
