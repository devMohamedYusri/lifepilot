"""Bookmarks router for smart bookmark management."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import json

from models import (
    BookmarkCreate, BookmarkUpdate, BookmarkResponse, 
    BookmarkStats, ReadingQueueRequest, ReadingQueueResponse, ReadingQueueItem
)
from database import execute_query, execute_write
from services.bookmark_analyzer import fetch_url_metadata, analyze_bookmark, generate_reading_queue

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


@router.post("", response_model=BookmarkResponse)
async def create_bookmark(bookmark: BookmarkCreate):
    """Create a new bookmark with AI analysis."""
    try:
        # Fetch URL metadata
        metadata = fetch_url_metadata(bookmark.url)
        
        # AI analysis
        analysis = analyze_bookmark(
            bookmark.url,
            metadata.get("title"),
            metadata.get("description")
        )
        
        # Insert into database
        query = """
            INSERT INTO bookmarks (
                url, title, description, favicon_url,
                category, topic_tags, estimated_minutes, complexity,
                summary, key_takeaways, source, user_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            bookmark.url,
            metadata.get("title"),
            metadata.get("description"),
            metadata.get("favicon_url"),
            analysis.get("category"),
            json.dumps(analysis.get("topic_tags", [])),
            analysis.get("estimated_minutes"),
            analysis.get("complexity"),
            analysis.get("summary"),
            json.dumps(analysis.get("key_takeaways", [])),
            bookmark.source,
            bookmark.notes,
        )
        
        bookmark_id = execute_write(query, params)
        
        results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
        if not results:
            raise HTTPException(status_code=500, detail="Failed to create bookmark")
        
        return BookmarkResponse(**results[0])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating bookmark: {str(e)}")


@router.get("", response_model=List[BookmarkResponse])
async def list_bookmarks(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    complexity: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query("created_at", pattern="^(created_at|priority|estimated_minutes|return_date)$")
):
    """List bookmarks with filters."""
    query = "SELECT * FROM bookmarks WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if complexity:
        query += " AND complexity = ?"
        params.append(complexity)
    
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    
    if tag:
        query += " AND topic_tags LIKE ?"
        params.append(f"%{tag}%")
    
    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR summary LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])
    
    # Sort order
    sort_map = {
        "created_at": "created_at DESC",
        "priority": "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC",
        "estimated_minutes": "estimated_minutes ASC",
        "return_date": "return_date ASC NULLS LAST, created_at DESC"
    }
    query += f" ORDER BY {sort_map.get(sort, 'created_at DESC')}"
    
    results = execute_query(query, tuple(params))
    return [BookmarkResponse(**row) for row in results]


@router.get("/reading-queue", response_model=ReadingQueueResponse)
async def get_reading_queue(
    minutes: int = Query(30, ge=5, le=480),
    energy: str = Query("medium", pattern="^(high|medium|low)$")
):
    """Get AI-powered reading suggestions."""
    # Get unread and in_progress bookmarks
    query = """
        SELECT * FROM bookmarks 
        WHERE status IN ('unread', 'in_progress')
        ORDER BY priority DESC, created_at DESC
    """
    bookmarks = execute_query(query)
    
    # Generate AI queue
    queue_result = generate_reading_queue(bookmarks, minutes, energy)
    
    # Get full bookmark objects for queue items
    queue_ids = [item.get("id") for item in queue_result.get("queue", [])]
    queue_bookmarks = []
    
    for qid in queue_ids:
        for b in bookmarks:
            if b.get("id") == qid:
                queue_bookmarks.append(BookmarkResponse(**b))
                break
    
    return ReadingQueueResponse(
        queue=[ReadingQueueItem(**item) for item in queue_result.get("queue", [])],
        total_time=queue_result.get("total_time", 0),
        encouragement=queue_result.get("encouragement", ""),
        bookmarks=queue_bookmarks
    )


@router.get("/stats", response_model=BookmarkStats)
async def get_bookmark_stats():
    """Get bookmark statistics."""
    all_bookmarks = execute_query("SELECT * FROM bookmarks")
    
    stats = {
        "total": len(all_bookmarks),
        "unread": 0,
        "in_progress": 0,
        "completed": 0,
        "archived": 0,
        "by_category": {},
        "by_priority": {},
        "total_estimated_minutes": 0,
        "total_completed_minutes": 0
    }
    
    for b in all_bookmarks:
        # Status counts
        status = b.get("status", "unread")
        if status in stats:
            stats[status] += 1
        
        # Category counts
        category = b.get("category", "other")
        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        # Priority counts
        priority = b.get("priority", "medium")
        stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        
        # Time estimates
        mins = b.get("estimated_minutes") or 0
        stats["total_estimated_minutes"] += mins
        if status == "completed":
            stats["total_completed_minutes"] += mins
    
    return BookmarkStats(**stats)


@router.get("/{bookmark_id}", response_model=BookmarkResponse)
async def get_bookmark(bookmark_id: int):
    """Get a specific bookmark."""
    results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return BookmarkResponse(**results[0])


@router.patch("/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(bookmark_id: int, update: BookmarkUpdate):
    """Update a bookmark."""
    results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    updates = []
    params = []
    
    if update.status is not None:
        updates.append("status = ?")
        params.append(update.status.value)
    
    if update.progress_percent is not None:
        updates.append("progress_percent = ?")
        params.append(update.progress_percent)
    
    if update.priority is not None:
        updates.append("priority = ?")
        params.append(update.priority.value)
    
    if update.return_date is not None:
        updates.append("return_date = ?")
        params.append(update.return_date)
    
    if update.user_notes is not None:
        updates.append("user_notes = ?")
        params.append(update.user_notes)
    
    if updates:
        params.append(bookmark_id)
        query = f"UPDATE bookmarks SET {', '.join(updates)} WHERE id = ?"
        execute_write(query, tuple(params))
    
    results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    return BookmarkResponse(**results[0])


@router.post("/{bookmark_id}/start-session", response_model=BookmarkResponse)
async def start_session(bookmark_id: int):
    """Start a reading session for a bookmark."""
    results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    bookmark = results[0]
    new_sessions = (bookmark.get("sessions_spent") or 0) + 1
    new_status = "in_progress" if bookmark.get("status") == "unread" else bookmark.get("status")
    
    query = """
        UPDATE bookmarks SET 
            sessions_spent = ?,
            last_accessed_at = ?,
            status = ?
        WHERE id = ?
    """
    execute_write(query, (new_sessions, datetime.now().isoformat(), new_status, bookmark_id))
    
    results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    return BookmarkResponse(**results[0])


@router.post("/{bookmark_id}/complete", response_model=BookmarkResponse)
async def complete_bookmark(bookmark_id: int):
    """Mark a bookmark as completed."""
    results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    query = """
        UPDATE bookmarks SET 
            status = 'completed',
            progress_percent = 100,
            completed_at = ?
        WHERE id = ?
    """
    execute_write(query, (datetime.now().isoformat(), bookmark_id))
    
    results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    return BookmarkResponse(**results[0])


@router.delete("/{bookmark_id}")
async def delete_bookmark(bookmark_id: int):
    """Delete a bookmark."""
    results = execute_query("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    execute_write("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
    return {"message": "Bookmark deleted successfully"}
