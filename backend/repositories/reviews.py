"""
Reviews repository for weekly/daily reviews.
"""
from typing import List, Optional
from core.repository import BaseRepository
from models import Review, ReviewCreate

class ReviewRepository(BaseRepository[Review]):
    """Repository for Review operations."""
    
    def __init__(self):
        super().__init__(model_class=Review, table_name="reviews")
        
    def find_latest(self, review_type: Optional[str] = None) -> Optional[Review]:
        """Find the most recent review, optionally by type."""
        try:
            filters = {"review_type": review_type} if review_type else None
            results = self.find_all(filters=filters, limit=1, order_by="created_at DESC")
            return results[0] if results else None
        except Exception:
            return None
