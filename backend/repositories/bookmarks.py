"""
Bookmarks repository for managing saved links.
"""
from typing import List, Optional

from core.repository import BaseRepository
from models import Bookmark

class BookmarkRepository(BaseRepository[Bookmark]):
    """Repository for Bookmark operations."""
    
    def __init__(self):
        super().__init__(model_class=Bookmark, table_name="bookmarks")
        
    def find_unread(self, limit: int = 100) -> List[Bookmark]:
        """Find unread bookmarks."""
        return self.find_all(filters={"is_read": False}, limit=limit)
        
    def find_by_url(self, url: str) -> Optional[Bookmark]:
        """Find bookmark by URL."""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE url = ?", (url,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return self.model_class(**dict(row))
            
        except Exception as e:
            raise DatabaseError("find_by_url", str(e))
