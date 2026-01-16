"""
Notifications repository for system alerts.
"""
from typing import List 
from core.repository import BaseRepository
from models import Notification

class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification operations."""
    
    def __init__(self):
        super().__init__(model_class=Notification, table_name="notifications")
        
    def find_unread(self, limit: int = 50) -> List[Notification]:
        """Find unread notifications."""
        return self.find_all(filters={"is_read": False}, limit=limit, order_by="created_at DESC")
    
    def mark_all_read(self) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {self.table_name} SET is_read = 1 WHERE is_read = 0")
            count = cursor.rowcount
            conn.commit()
            return count
        except Exception as e:
            raise DatabaseError("mark_all_read", str(e))
