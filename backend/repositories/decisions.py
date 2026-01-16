"""
Decisions repository for the decision journal.
"""
from typing import List, Optional
import sqlite3

from core.repository import BaseRepository
from models import DecisionResponse, DecisionCreate, DecisionUpdate

class DecisionRepository(BaseRepository[DecisionResponse]):
    """Repository for Decision operations."""
    
    def __init__(self):
        super().__init__(model_class=DecisionResponse, table_name="decisions")
        
    def find_pending(self, limit: int = 20) -> List[DecisionResponse]:
        """Find pending decisions."""
        try:
            return self.find_all(filters={"status": "deliberating"}, limit=limit)
        except Exception as e:
            # Fallback if filters fail or schema differs
             return self.find_all(limit=limit)

    def find_by_item_id(self, item_id: int) -> Optional[DecisionResponse]:
        """Find decision linked to an item."""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE item_id = ?", (item_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return self.model_class(**dict(row))
        except Exception as e:
            raise DatabaseError("find_by_item_id", str(e))
