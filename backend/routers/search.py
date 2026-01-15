"""Search router for natural language search."""
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel

from services.search_service import perform_search

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    """Request model for search."""
    query: str
    types: Optional[List[str]] = None  # items, bookmarks, decisions


class SearchResult(BaseModel):
    """Individual search result."""
    id: int
    type: str  # item, bookmark, decision
    title: Optional[str] = None
    snippet: Optional[str] = None
    relevance_score: float = 0.5
    relevance_reason: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    # Item-specific
    item_type: Optional[str] = None
    priority: Optional[str] = None
    # Bookmark-specific
    category: Optional[str] = None
    # Decision-specific
    chosen_option: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model for search."""
    query: str
    interpreted_as: str
    results: List[dict]
    total_found: int
    search_time_ms: int


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search across items, bookmarks, and decisions."""
    result = perform_search(request.query, request.types)
    
    # Format results with proper titles and snippets
    formatted_results = []
    for r in result.get("results", []):
        formatted = {
            "id": r.get("id"),
            "type": r.get("type"),
            "relevance_score": r.get("relevance_score", 0.5),
            "relevance_reason": r.get("relevance_reason", ""),
            "created_at": r.get("created_at"),
        }
        
        if r.get("type") == "item":
            formatted["title"] = r.get("ai_summary") or r.get("raw_content", "")[:100]
            formatted["snippet"] = r.get("ai_next_action") or r.get("raw_content", "")[:150]
            formatted["item_type"] = r.get("item_type")
            formatted["priority"] = r.get("priority")
            formatted["status"] = r.get("status")
        
        elif r.get("type") == "bookmark":
            formatted["title"] = r.get("title") or r.get("url", "")
            formatted["snippet"] = r.get("summary") or r.get("description") or ""
            formatted["url"] = r.get("url")
            formatted["category"] = r.get("category")
            formatted["status"] = r.get("status")
        
        elif r.get("type") == "decision":
            formatted["title"] = r.get("context") or r.get("situation") or "Decision"
            formatted["snippet"] = r.get("reasoning") or r.get("chosen_option") or ""
            formatted["status"] = r.get("status")
            formatted["chosen_option"] = r.get("chosen_option")
        
        formatted_results.append(formatted)
    
    return SearchResponse(
        query=result.get("query", request.query),
        interpreted_as=result.get("interpreted_as", request.query),
        results=formatted_results,
        total_found=result.get("total_found", 0),
        search_time_ms=result.get("search_time_ms", 0)
    )


@router.get("/suggestions")
async def get_suggestions():
    """Return suggested queries based on user's data."""
    return {
        "recent": [],  # Could store in DB
        "suggested": [
            "Unread bookmarks",
            "Pending decisions",
            "High priority tasks",
            "Waiting for replies",
            "Articles about technology"
        ]
    }
