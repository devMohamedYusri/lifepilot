"""
Agent Memory System

Handles storing, retrieving, and managing agent long-term memory.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import execute_query, execute_write

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages agent long-term memory storage and retrieval."""
    
    def __init__(self):
        self.max_memories = 1000  # Maximum memories to store
        self.decay_threshold_days = 90  # Days before memory importance decays
    
    def store_memory(
        self,
        memory_type: str,
        content: str,
        category: Optional[str] = None,
        importance: float = 0.5
    ) -> int:
        """
        Store a new memory.
        
        Args:
            memory_type: preference, pattern, fact, or episode
            content: The memory content
            category: Optional category for organization
            importance: Importance score 0.0-1.0
            
        Returns:
            ID of the created memory
        """
        # Check for duplicate memories
        existing = execute_query("""
            SELECT id FROM agent_memory 
            WHERE memory_type = ? AND content = ?
        """, (memory_type, content))
        
        if existing:
            # Update access count instead of creating duplicate
            self.access_memory(existing[0]['id'])
            return existing[0]['id']
        
        memory_id = execute_write("""
            INSERT INTO agent_memory 
            (memory_type, category, content, importance_score, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (memory_type, category, content, importance))
        
        # Cleanup if too many memories
        self._cleanup_old_memories()
        
        logger.info(f"Stored memory: {memory_type}/{category} (importance: {importance})")
        return memory_id
    
    def retrieve_memories(
        self,
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories.
        
        Args:
            query: Optional search query (simple text matching for now)
            memory_type: Filter by memory type
            category: Filter by category
            limit: Maximum memories to return
            
        Returns:
            List of memory dictionaries
        """
        sql = "SELECT * FROM agent_memory WHERE 1=1"
        params = []
        
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        
        if query:
            # Simple text search (could be enhanced with embeddings)
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")
        
        sql += " ORDER BY importance_score DESC, access_count DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        memories = execute_query(sql, tuple(params))
        
        # Update access timestamps
        for memory in memories:
            self.access_memory(memory['id'])
        
        return memories
    
    def access_memory(self, memory_id: int):
        """Record that a memory was accessed."""
        execute_write("""
            UPDATE agent_memory 
            SET access_count = access_count + 1,
                last_accessed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (memory_id,))
    
    def update_importance(self, memory_id: int, new_importance: float):
        """Update a memory's importance score."""
        execute_write("""
            UPDATE agent_memory 
            SET importance_score = ?
            WHERE id = ?
        """, (new_importance, memory_id))
    
    def delete_memory(self, memory_id: int):
        """Delete a specific memory."""
        execute_write("DELETE FROM agent_memory WHERE id = ?", (memory_id,))
    
    def get_user_preferences(self) -> List[Dict[str, Any]]:
        """Get all stored user preferences."""
        return self.retrieve_memories(memory_type="preference", limit=50)
    
    def get_user_facts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get stored facts about the user."""
        return self.retrieve_memories(memory_type="fact", category=category, limit=50)
    
    def get_recent_episodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent episodic memories (notable interactions)."""
        return execute_query("""
            SELECT * FROM agent_memory 
            WHERE memory_type = 'episode'
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
    
    def decay_unused_memories(self):
        """
        Reduce importance of old, unused memories.
        Called periodically to prevent memory bloat.
        """
        threshold_date = (datetime.now() - timedelta(days=self.decay_threshold_days)).isoformat()
        
        # Decay memories not accessed in threshold period
        execute_write("""
            UPDATE agent_memory
            SET importance_score = importance_score * 0.9
            WHERE (last_accessed_at IS NULL OR last_accessed_at < ?)
            AND importance_score > 0.1
        """, (threshold_date,))
        
        # Delete very low importance memories
        execute_write("""
            DELETE FROM agent_memory
            WHERE importance_score < 0.1
            AND memory_type != 'preference'
        """)
        
        logger.info("Memory decay completed")
    
    def _cleanup_old_memories(self):
        """Remove excess memories if over limit."""
        count_result = execute_query("SELECT COUNT(*) as count FROM agent_memory")
        count = count_result[0]['count'] if count_result else 0
        
        if count > self.max_memories:
            # Delete lowest importance, oldest memories
            excess = count - self.max_memories
            execute_write("""
                DELETE FROM agent_memory
                WHERE id IN (
                    SELECT id FROM agent_memory
                    WHERE memory_type NOT IN ('preference')
                    ORDER BY importance_score ASC, access_count ASC, created_at ASC
                    LIMIT ?
                )
            """, (excess,))
            logger.info(f"Cleaned up {excess} old memories")
    
    def extract_memories_from_interaction(
        self,
        user_message: str,
        agent_response: str,
        actions_taken: List[Dict],
        llm_client = None
    ) -> List[Dict[str, Any]]:
        """
        Extract memorable information from an interaction.
        
        This would ideally use the LLM to identify what's worth remembering.
        For now, uses simple heuristics.
        """
        memories_to_store = []
        
        # Look for explicit preferences
        preference_keywords = ['i prefer', 'i like', 'i hate', 'i always', 'i never', 'i usually']
        message_lower = user_message.lower()
        
        for keyword in preference_keywords:
            if keyword in message_lower:
                memories_to_store.append({
                    'type': 'preference',
                    'category': 'communication',
                    'content': user_message,
                    'importance': 0.7
                })
                break
        
        # Store successful action patterns
        for action in actions_taken:
            if action.get('status') == 'completed':
                memories_to_store.append({
                    'type': 'episode',
                    'category': action.get('action_type', 'general'),
                    'content': f"User requested: {user_message}. Action taken: {action.get('action_type')}",
                    'importance': 0.5
                })
        
        # Actually store the memories
        for memory in memories_to_store:
            self.store_memory(
                memory_type=memory['type'],
                content=memory['content'],
                category=memory.get('category'),
                importance=memory.get('importance', 0.5)
            )
        
        return memories_to_store
    
    def get_context_for_conversation(self, user_message: str) -> Dict[str, Any]:
        """
        Get relevant memory context for a new conversation message.
        
        Args:
            user_message: The user's message
            
        Returns:
            Dict with preferences, facts, and relevant episodes
        """
        return {
            'preferences': self.get_user_preferences(),
            'facts': self.get_user_facts(),
            'recent_episodes': self.get_recent_episodes(limit=5),
            # Could add semantic search here based on user_message
        }
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories."""
        stats = execute_query("""
            SELECT 
                memory_type,
                COUNT(*) as count,
                AVG(importance_score) as avg_importance,
                SUM(access_count) as total_accesses
            FROM agent_memory
            GROUP BY memory_type
        """)
        
        total = execute_query("SELECT COUNT(*) as count FROM agent_memory")
        
        return {
            'total_memories': total[0]['count'] if total else 0,
            'by_type': {s['memory_type']: s for s in stats}
        }


# Singleton instance
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """Get the singleton memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
