"""
Energy repository for tracking energy levels.
"""
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3

from core.repository import BaseRepository
from models import EnergyLog, EnergyLogCreate

class EnergyRepository(BaseRepository[EnergyLog]):
    """Repository for EnergyLog operations."""
    
    def __init__(self):
        super().__init__(model_class=EnergyLog, table_name="energy_logs")
        
    def find_by_date_range(self, start_date: str, end_date: str) -> List[EnergyLog]:
        """Find energy logs within a date range."""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = f"SELECT * FROM {self.table_name} WHERE created_at BETWEEN ? AND ? ORDER BY created_at ASC"
            cursor.execute(query, (start_date, end_date))
            
            rows = cursor.fetchall()
            return [self.model_class(**dict(row)) for row in rows]
        except Exception as e:
            raise DatabaseError("find_by_date_range", str(e))

    def get_todays_logs(self) -> List[EnergyLog]:
        """Get logs for the current day."""
        today = datetime.now().strftime("%Y-%m-%d")
        start = f"{today}T00:00:00"
        end = f"{today}T23:59:59"
        return self.find_by_date_range(start, end)
