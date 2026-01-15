"""Items router for CRUD operations on items."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta

from models import ItemCreate, ItemUpdate, ItemResponse, ItemType, ItemStatus, FollowUpRequest, RecurrenceUpdate
from database import execute_query, execute_write
from services.categorizer import categorize_input

router = APIRouter(prefix="/api/items", tags=["items"])


def _calculate_follow_up_date(days: int) -> str:
    """Calculate follow-up date from now."""
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def _calculate_next_recurrence(pattern: str, interval: int, from_date: str = None) -> str:
    """Calculate next recurrence date based on pattern."""
    base = datetime.strptime(from_date, "%Y-%m-%d") if from_date else datetime.now()
    
    if pattern == "daily":
        next_date = base + timedelta(days=interval)
    elif pattern == "weekly":
        next_date = base + timedelta(weeks=interval)
    elif pattern == "monthly":
        # Add months (approximate)
        next_date = base + timedelta(days=30 * interval)
    elif pattern == "yearly":
        next_date = base + timedelta(days=365 * interval)
    else:
        next_date = base + timedelta(days=interval)
    
    return next_date.strftime("%Y-%m-%d")


@router.post("", response_model=ItemResponse)
async def create_item(item: ItemCreate):
    """
    Create a new item from raw text input.
    The input will be processed by AI for categorization.
    """
    try:
        # Categorize using AI
        categorization = categorize_input(item.content)
        
        # Calculate follow-up date for waiting_for items
        follow_up_date = None
        if categorization.get("type") == "waiting_for" and categorization.get("follow_up_days"):
            follow_up_date = _calculate_follow_up_date(categorization["follow_up_days"])
        
        # Calculate recurrence next date for life_admin items
        recurrence_next_date = None
        recurrence_pattern = categorization.get("recurrence_pattern")
        recurrence_interval = categorization.get("recurrence_interval", 1) or 1
        if recurrence_pattern:
            recurrence_next_date = _calculate_next_recurrence(recurrence_pattern, recurrence_interval)
        
        # Insert into database
        query = """
            INSERT INTO items (
                raw_content, type, status, priority, energy_required,
                context, due_date, person_involved, ai_summary, ai_next_action,
                follow_up_date, recurrence_pattern, recurrence_interval, recurrence_next_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            item.content,
            categorization.get("type", "note"),
            "active",
            categorization.get("priority", "medium"),
            categorization.get("energy_required", "medium"),
            categorization.get("context"),
            categorization.get("due_date"),
            categorization.get("person_involved"),
            categorization.get("summary"),
            categorization.get("next_action"),
            follow_up_date,
            recurrence_pattern,
            recurrence_interval,
            recurrence_next_date,
        )
        
        item_id = execute_write(query, params)
        
        # Fetch and return the created item
        results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
        if not results:
            raise HTTPException(status_code=500, detail="Failed to create item")
        
        return ItemResponse(**results[0])
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing item: {str(e)}")


@router.get("/needs-followup", response_model=List[ItemResponse])
async def get_needs_followup():
    """Get waiting_for items that need follow-up attention."""
    today = datetime.now().strftime("%Y-%m-%d")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    query = """
        SELECT * FROM items 
        WHERE type = 'waiting_for' 
        AND status = 'active'
        AND (
            (follow_up_date IS NOT NULL AND follow_up_date <= ?)
            OR (follow_up_date IS NULL AND created_at <= ?)
        )
        ORDER BY follow_up_date ASC, created_at ASC
    """
    results = execute_query(query, (today, three_days_ago))
    return [ItemResponse(**row) for row in results]


@router.get("/upcoming-recurring", response_model=List[ItemResponse])
async def get_upcoming_recurring():
    """Get life_admin items with recurrence, sorted by next date."""
    query = """
        SELECT * FROM items 
        WHERE recurrence_pattern IS NOT NULL 
        AND status = 'active'
        ORDER BY recurrence_next_date ASC
    """
    results = execute_query(query)
    return [ItemResponse(**row) for row in results]


@router.get("", response_model=List[ItemResponse])
async def list_items(
    type: Optional[ItemType] = Query(None, description="Filter by item type"),
    status: Optional[ItemStatus] = Query(None, description="Filter by status"),
    include_snoozed: bool = Query(False, description="Include snoozed items")
):
    """List all items with optional filters."""
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    
    if type:
        query += " AND type = ?"
        params.append(type.value)
    
    if status:
        query += " AND status = ?"
        params.append(status.value)
    else:
        query += " AND status NOT IN ('done', 'archived')"
    
    if not include_snoozed:
        query += " AND (snoozed_until IS NULL OR snoozed_until <= ?)"
        params.append(datetime.now().strftime("%Y-%m-%d"))
    
    query += " ORDER BY created_at DESC"
    
    results = execute_query(query, tuple(params))
    return [ItemResponse(**row) for row in results]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    """Get a specific item by ID."""
    results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(**results[0])


@router.post("/{item_id}/follow-up", response_model=ItemResponse)
async def record_follow_up(item_id: int, follow_up: FollowUpRequest):
    """Record a follow-up for a waiting_for item."""
    results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item = results[0]
    if item["type"] != "waiting_for":
        raise HTTPException(status_code=400, detail="Follow-up only for waiting_for items")
    
    # Increment count and set new follow-up date (3 days from now)
    new_count = (item.get("follow_up_count") or 0) + 1
    new_follow_up_date = _calculate_follow_up_date(3)
    
    query = """
        UPDATE items SET 
            follow_up_count = ?,
            follow_up_date = ?,
            last_follow_up_note = ?,
            updated_at = ?
        WHERE id = ?
    """
    execute_write(query, (new_count, new_follow_up_date, follow_up.note, datetime.now().isoformat(), item_id))
    
    results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    return ItemResponse(**results[0])


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, update: ItemUpdate):
    """Update an item (status, snooze, etc.)."""
    results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item = results[0]
    updates = []
    params = []
    
    if update.status is not None:
        updates.append("status = ?")
        params.append(update.status.value)
        
        # Phase 2: Handle recurring item completion
        if update.status.value == "done" and item.get("recurrence_pattern"):
            _create_next_recurrence(item)
    
    if update.priority is not None:
        updates.append("priority = ?")
        params.append(update.priority.value)
    
    if update.snoozed_until is not None:
        updates.append("snoozed_until = ?")
        params.append(update.snoozed_until)
    
    if update.due_date is not None:
        updates.append("due_date = ?")
        params.append(update.due_date)
    
    if not updates:
        return ItemResponse(**results[0])
    
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(item_id)
    
    query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
    execute_write(query, tuple(params))
    
    results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    return ItemResponse(**results[0])


def _create_next_recurrence(item: dict):
    """Create next occurrence for a recurring item."""
    pattern = item.get("recurrence_pattern")
    interval = item.get("recurrence_interval", 1) or 1
    current_next = item.get("recurrence_next_date")
    end_date = item.get("recurrence_end_date")
    
    # Calculate new next date
    new_next_date = _calculate_next_recurrence(pattern, interval, current_next)
    
    # Check if past end date
    if end_date and new_next_date > end_date:
        return  # Don't create more occurrences
    
    # Create new item
    query = """
        INSERT INTO items (
            raw_content, type, status, priority, energy_required,
            context, due_date, person_involved, ai_summary, ai_next_action,
            recurrence_pattern, recurrence_interval, recurrence_next_date, 
            recurrence_end_date, parent_item_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        item["raw_content"],
        item["type"],
        "active",
        item.get("priority", "medium"),
        item.get("energy_required", "medium"),
        item.get("context"),
        new_next_date,  # Set due_date to next occurrence
        item.get("person_involved"),
        item.get("ai_summary"),
        item.get("ai_next_action"),
        pattern,
        interval,
        _calculate_next_recurrence(pattern, interval, new_next_date),
        end_date,
        item["id"],
    )
    execute_write(query, params)


@router.patch("/{item_id}/recurrence", response_model=ItemResponse)
async def update_recurrence(item_id: int, recurrence: RecurrenceUpdate):
    """Update recurrence settings for an item."""
    results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Item not found")
    
    updates = []
    params = []
    
    if recurrence.recurrence_pattern is not None:
        updates.append("recurrence_pattern = ?")
        params.append(recurrence.recurrence_pattern)
        
        # Calculate next date if setting a pattern
        if recurrence.recurrence_pattern:
            interval = recurrence.recurrence_interval or 1
            next_date = _calculate_next_recurrence(recurrence.recurrence_pattern, interval)
            updates.append("recurrence_next_date = ?")
            params.append(next_date)
    
    if recurrence.recurrence_interval is not None:
        updates.append("recurrence_interval = ?")
        params.append(recurrence.recurrence_interval)
    
    if recurrence.recurrence_end_date is not None:
        updates.append("recurrence_end_date = ?")
        params.append(recurrence.recurrence_end_date)
    
    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(item_id)
        
        query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        execute_write(query, tuple(params))
    
    results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    return ItemResponse(**results[0])


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    """Delete an item."""
    results = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Item not found")
    
    execute_write("DELETE FROM items WHERE id = ?", (item_id,))
    return {"message": "Item deleted successfully"}

