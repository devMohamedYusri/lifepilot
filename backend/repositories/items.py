"""
Items repository for managing tasks, notes, etc.
"""
from typing import List, Optional

from core.repository import BaseRepository
from models import Item, ItemCreate, ItemUpdate

class ItemRepository(BaseRepository[Item]):
    """Repository for Item operations."""
    
    def __init__(self):
        super().__init__(model_class=Item, table_name="items")
        
    def find_by_status(self, status: str, limit: int = 100) -> List[Item]:
        """Find items by status."""
        return self.find_all(filters={"status": status}, limit=limit)
        
    def find_proactive_candidates(self, limit: int = 10) -> List[Item]:
        """Find items that need attention (active and high priority)."""
        # specialized query for proactive suggestions
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM items 
                WHERE status IN ('active', 'in_progress') 
                AND priority = 'high'
                ORDER BY created_at DESC 
                LIMIT ?
            """
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [self.model_class(**dict(row)) for row in rows]
        except Exception as e:
            raise DatabaseError("find_proactive_candidates", str(e))

    def search(self, query: str) -> List[Item]:
        """Full text search on items."""
        # Simple LIKE search for now
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            sql = f"SELECT * FROM {self.table_name} WHERE content LIKE ? OR category LIKE ? LIMIT 50"
            term = f"%{query}%"
            cursor.execute(sql, (term, term))
            
            rows = cursor.fetchall()
            return [self.model_class(**dict(row)) for row in rows]
        except Exception as e:
            raise DatabaseError("search", str(e))
