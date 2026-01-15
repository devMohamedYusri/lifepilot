"""Focus router for Today's Focus AI selection."""
from fastapi import APIRouter, HTTPException
from typing import List

from models import TodayFocusResponse, ItemResponse, FocusItem
from database import execute_query
from services.focus_picker import pick_focus_items

router = APIRouter(prefix="/api/focus", tags=["focus"])


@router.get("/today", response_model=TodayFocusResponse)
async def get_today_focus():
    """
    Get AI-selected focus items for today.
    Considers priority, due dates, energy levels, and context variety.
    """
    try:
        # Get all active items
        query = """
            SELECT * FROM items 
            WHERE status = 'active' 
            AND (snoozed_until IS NULL OR snoozed_until <= date('now'))
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END,
                due_date ASC NULLS LAST,
                created_at ASC
        """
        items = execute_query(query)
        
        if not items:
            return TodayFocusResponse(
                focus_items=[],
                encouragement="Your inbox is clear! Time to capture some new tasks.",
                items=[]
            )
        
        # Use AI to pick focus items
        focus_result = pick_focus_items(items)
        
        # Get full item details for focus items
        focus_ids = {fi["id"] for fi in focus_result.get("focus_items", [])}
        focus_items_full = [
            ItemResponse(**item) for item in items 
            if item["id"] in focus_ids
        ]
        
        # Build response
        return TodayFocusResponse(
            focus_items=[
                FocusItem(id=fi["id"], reason=fi["reason"])
                for fi in focus_result.get("focus_items", [])
            ],
            encouragement=focus_result.get("encouragement", "Let's make today count!"),
            items=focus_items_full
        )
        
    except ValueError as e:
        # Handle missing API key
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting focus: {str(e)}")
