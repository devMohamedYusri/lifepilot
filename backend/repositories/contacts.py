"""
Contacts repository for managing people and CRM data.
"""
from typing import List, Optional
from datetime import datetime
import sqlite3

from core.repository import BaseRepository
from models import Contact, ContactCreate, ContactUpdate
from core.exceptions import DatabaseError

class ContactRepository(BaseRepository[Contact]):
    """Repository for Contact operations."""
    
    def __init__(self):
        super().__init__(model_class=Contact, table_name="contacts")
        
    def find_proactive_candidates(self) -> List[Contact]:
        """Find contacts that need attention based on reachout frequency."""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Simple check for now: anyone with last_contacted longer than reachout_frequency days
            # This is a simplified logic - real logic would do date math in SQL or python service
            query = """
                SELECT * FROM contacts 
                WHERE reachout_frequency IS NOT NULL 
                ORDER BY last_contacted ASC 
                LIMIT 5
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self.model_class(**dict(row)) for row in rows]
        except Exception as e:
            raise DatabaseError("find_proactive_candidates", str(e))

    def search(self, query: str) -> List[Contact]:
        """Search contacts by name, role, or company."""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            term = f"%{query}%"
            sql = f"""
                SELECT * FROM {self.table_name} 
                WHERE name LIKE ? OR role LIKE ? OR company LIKE ? 
                LIMIT 20
            """
            cursor.execute(sql, (term, term, term))
            
            rows = cursor.fetchall()
            return [self.model_class(**dict(row)) for row in rows]
        except Exception as e:
            raise DatabaseError("search", str(e))
