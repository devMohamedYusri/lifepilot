"""
Base repository pattern for database operations.
"""
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union
from datetime import datetime
import sqlite3
import json

from pydantic import BaseModel

from database import get_connection
from core.exceptions import NotFoundError, DatabaseError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseRepository(Generic[T]):
    """
    Base repository implementing common database operations.
    
    Args:
        model_class: Pydantic model class for validation/serialization
        table_name: Database table name
    """
    
    def __init__(self, model_class: Type[T], table_name: str):
        self.model_class = model_class
        self.table_name = table_name
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return get_connection()
        
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary."""
        return dict(row)
        
    def _parse_json_fields(self, data: Dict[str, Any], json_fields: List[str]) -> Dict[str, Any]:
        """Parse JSON strings back to objects."""
        for field in json_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string or whatever it is if parsing fails
        return data

    def count(self) -> int:
        """Count total records."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Count failed for {self.table_name}: {e}")
            raise DatabaseError("count", str(e))
            
    def find_all(
        self, 
        limit: int = 100, 
        offset: int = 0, 
        order_by: str = "created_at DESC",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """
        Find all records with optional filtering and pagination.
        """
        try:
            query = f"SELECT * FROM {self.table_name}"
            params = []
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"{key} = ?")
                    params.append(value)
                query += " WHERE " + " AND ".join(conditions)
                
            query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            return [self.model_class(**dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Find all failed for {self.table_name}: {e}")
            raise DatabaseError("find_all", str(e))

    def find_by_id(self, id: Any) -> Optional[T]:
        """Find a record by ID."""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return self.model_class(**dict(row))
            
        except Exception as e:
            logger.error(f"Find by ID failed for {self.table_name}: {e}")
            raise DatabaseError("find_by_id", str(e))
            
    def create(self, data: Union[Dict[str, Any], BaseModel]) -> T:
        """Create a new record."""
        try:
            if isinstance(data, BaseModel):
                data_dict = data.model_dump(exclude_unset=True)
            else:
                data_dict = data.copy()
                
            # Handle timestamps
            if "created_at" not in data_dict:
                data_dict["created_at"] = datetime.now().isoformat()
            if "updated_at" not in data_dict:
                data_dict["updated_at"] = datetime.now().isoformat()
                
            columns = ", ".join(data_dict.keys())
            placeholders = ", ".join(["?" for _ in data_dict])
            values = list(data_dict.values())
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})",
                values
            )
            data_dict["id"] = cursor.lastrowid
            conn.commit()
            
            return self.model_class(**data_dict)
            
        except Exception as e:
            logger.error(f"Create failed for {self.table_name}: {e}")
            raise DatabaseError("create", str(e))
            
    def update(self, id: Any, data: Union[Dict[str, Any], BaseModel]) -> T:
        """Update an existing record."""
        try:
            # Check if exists first
            existing = self.find_by_id(id)
            if not existing:
                raise NotFoundError(self.table_name, id)
                
            if isinstance(data, BaseModel):
                data_dict = data.model_dump(exclude_unset=True)
            else:
                data_dict = data.copy()
                
            # Update timestamp
            data_dict["updated_at"] = datetime.now().isoformat()
            
            # Remove id from update if present
            if "id" in data_dict:
                del data_dict["id"]
                
            set_clause = ", ".join([f"{key} = ?" for key in data_dict.keys()])
            values = list(data_dict.values())
            values.append(id)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?",
                values
            )
            conn.commit()
            
            return self.find_by_id(id)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Update failed for {self.table_name}: {e}")
            raise DatabaseError("update", str(e))
            
    def delete(self, id: Any) -> bool:
        """Delete a record by ID."""
        try:
            # Check if exists first
            if not self.find_by_id(id):
                raise NotFoundError(self.table_name, id)
                
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (id,))
            conn.commit()
            
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Delete failed for {self.table_name}: {e}")
            raise DatabaseError("delete", str(e))
