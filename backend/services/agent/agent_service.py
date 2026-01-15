"""
Agent Service

Main service layer for the autonomous agent.
Handles conversation management, action approval, and settings.
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import execute_query, execute_write
from .graph import run_agent
from .memory import get_memory_manager
from .tools import get_tool_registry

logger = logging.getLogger(__name__)


class AgentService:
    """Main service for agent interactions."""
    
    def __init__(self):
        self.memory_manager = get_memory_manager()
        self.tool_registry = get_tool_registry()
    
    def chat(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to the agent and get a response.
        
        Args:
            message: User's message
            session_id: Optional session ID (creates new if not provided)
            
        Returns:
            Agent response with any pending actions
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Store user message
        self._store_message(session_id, "user", message)
        
        # Run the agent graph
        result = run_agent(message, session_id)
        
        # Store assistant response
        if result.get("response"):
            self._store_message(
                session_id, 
                "assistant", 
                result["response"],
                tool_calls=result.get("tool_results"),
            )
        
        # Store pending actions
        pending_actions = []
        for action in result.get("pending_approvals", []):
            action_id = self._store_pending_action(session_id, action)
            action["id"] = action_id
            pending_actions.append(action)
        
        return {
            "session_id": session_id,
            "response": result.get("response", ""),
            "pending_actions": pending_actions,
            "suggestions": result.get("suggestions", []),
            "intent": result.get("intent", ""),
            "success": result.get("success", True),
        }
    
    def get_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of recent conversations."""
        # Get unique sessions with latest message
        sessions = execute_query("""
            SELECT 
                session_id,
                MIN(created_at) as started_at,
                MAX(created_at) as last_message_at,
                COUNT(*) as message_count
            FROM agent_conversations
            GROUP BY session_id
            ORDER BY last_message_at DESC
            LIMIT ?
        """, (limit,))
        
        # Get first user message for each session as preview
        for session in sessions:
            first_msg = execute_query("""
                SELECT content FROM agent_conversations
                WHERE session_id = ? AND role = 'user'
                ORDER BY created_at ASC
                LIMIT 1
            """, (session['session_id'],))
            
            session['preview'] = first_msg[0]['content'][:100] if first_msg else ""
        
        return sessions
    
    def get_conversation(self, session_id: str) -> Dict[str, Any]:
        """Get full conversation by session ID."""
        messages = execute_query("""
            SELECT * FROM agent_conversations
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))
        
        return {
            "session_id": session_id,
            "messages": messages,
            "message_count": len(messages),
            "created_at": messages[0]['created_at'] if messages else None,
            "last_message_at": messages[-1]['created_at'] if messages else None,
        }
    
    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get all actions awaiting user approval."""
        actions = execute_query("""
            SELECT * FROM agent_actions
            WHERE status = 'pending_approval'
            ORDER BY created_at DESC
        """)
        
        # Parse JSON fields
        for action in actions:
            if action.get('action_params'):
                try:
                    action['action_params'] = json.loads(action['action_params'])
                except:
                    pass
        
        return actions
    
    def approve_action(self, action_id: int) -> Dict[str, Any]:
        """Approve and execute a pending action."""
        # Get the action
        actions = execute_query(
            "SELECT * FROM agent_actions WHERE id = ?",
            (action_id,)
        )
        
        if not actions:
            return {"success": False, "error": "Action not found"}
        
        action = actions[0]
        
        if action['status'] != 'pending_approval':
            return {"success": False, "error": f"Action is not pending approval (status: {action['status']})"}
        
        # Update status to approved
        execute_write("""
            UPDATE agent_actions
            SET status = 'approved', approved_by = 'user', approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (action_id,))
        
        # Execute the action
        try:
            params = json.loads(action['action_params']) if action['action_params'] else {}
            tool = self.tool_registry.get_tool(action['action_type'])
            
            if tool:
                execute_write("""
                    UPDATE agent_actions
                    SET status = 'executing', execution_started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (action_id,))
                
                result = tool.function(params)
                
                execute_write("""
                    UPDATE agent_actions
                    SET status = 'completed', 
                        execution_completed_at = CURRENT_TIMESTAMP,
                        result_summary = ?
                    WHERE id = ?
                """, (json.dumps(result), action_id))
                
                return {"success": True, "result": result}
            else:
                execute_write("""
                    UPDATE agent_actions
                    SET status = 'failed', error_details = ?
                    WHERE id = ?
                """, ("Unknown tool", action_id))
                
                return {"success": False, "error": "Unknown tool"}
                
        except Exception as e:
            execute_write("""
                UPDATE agent_actions
                SET status = 'failed', error_details = ?
                WHERE id = ?
            """, (str(e), action_id))
            
            return {"success": False, "error": str(e)}
    
    def reject_action(self, action_id: int, feedback: Optional[str] = None) -> Dict[str, Any]:
        """Reject a pending action."""
        execute_write("""
            UPDATE agent_actions
            SET status = 'cancelled', error_details = ?
            WHERE id = ? AND status = 'pending_approval'
        """, (feedback or "Rejected by user", action_id))
        
        # Store feedback as memory for future learning
        if feedback:
            self.memory_manager.store_memory(
                memory_type="preference",
                content=f"User rejected action with feedback: {feedback}",
                category="action_feedback",
                importance=0.7
            )
        
        return {"success": True}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and statistics."""
        # Get settings
        settings = self.get_settings()
        
        # Get statistics
        stats = execute_query("""
            SELECT
                (SELECT COUNT(DISTINCT session_id) FROM agent_conversations) as total_conversations,
                (SELECT COUNT(*) FROM agent_actions WHERE status = 'completed') as total_actions_executed,
                (SELECT COUNT(*) FROM agent_actions WHERE status = 'pending_approval') as pending_actions,
                (SELECT COUNT(*) FROM agent_memory) as memory_count,
                (SELECT COUNT(*) FROM agent_goals WHERE status = 'active') as active_goals,
                (SELECT MAX(created_at) FROM agent_conversations) as last_activity_at
        """)
        
        stat = stats[0] if stats else {}
        
        return {
            "mode": settings.get("agent_mode", "assistant"),
            "is_active": True,
            "total_conversations": stat.get("total_conversations", 0),
            "total_actions_executed": stat.get("total_actions_executed", 0),
            "pending_actions": stat.get("pending_actions", 0),
            "memory_count": stat.get("memory_count", 0),
            "active_goals": stat.get("active_goals", 0),
            "last_activity_at": stat.get("last_activity_at"),
        }
    
    def get_settings(self) -> Dict[str, Any]:
        """Get agent settings."""
        rows = execute_query("SELECT key, value FROM agent_settings")
        
        settings = {}
        for row in rows:
            key = row['key']
            value = row['value']
            
            # Convert types
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.replace('.', '').isdigit():
                value = float(value) if '.' in value else int(value)
            
            settings[key] = value
        
        return settings
    
    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent settings."""
        for key, value in updates.items():
            # Convert value to string for storage
            str_value = str(value).lower() if isinstance(value, bool) else str(value)
            
            execute_write("""
                INSERT OR REPLACE INTO agent_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, str_value))
        
        return self.get_settings()
    
    def run_proactive_check(self) -> Dict[str, Any]:
        """
        Run proactive analysis and generate suggestions.
        
        This would be called periodically in proactive/autonomous modes.
        """
        settings = self.get_settings()
        
        if settings.get("agent_mode") == "assistant":
            return {
                "suggestions_generated": 0,
                "message": "Proactive checks disabled in assistant mode"
            }
        
        # Get current state for analysis
        items_summary = execute_query("""
            SELECT 
                COUNT(CASE WHEN due_date < date('now') AND status = 'active' THEN 1 END) as overdue,
                COUNT(CASE WHEN due_date = date('now') AND status = 'active' THEN 1 END) as due_today,
                COUNT(CASE WHEN status = 'inbox' THEN 1 END) as inbox
            FROM items
        """)
        
        contacts_overdue = execute_query("""
            SELECT COUNT(*) as count FROM contacts
            WHERE next_contact_date < date('now') AND is_active = 1
        """)
        
        suggestions = []
        
        # Check for overdue items
        if items_summary and items_summary[0].get('overdue', 0) > 0:
            count = items_summary[0]['overdue']
            suggestions.append({
                "type": "nudge",
                "title": "Overdue items need attention",
                "message": f"You have {count} overdue item(s). Would you like to review them?",
                "priority": "high"
            })
        
        # Check for contacts needing attention
        if contacts_overdue and contacts_overdue[0].get('count', 0) > 0:
            count = contacts_overdue[0]['count']
            suggestions.append({
                "type": "reminder",
                "title": "Contacts to reconnect with",
                "message": f"{count} contact(s) are overdue for follow-up.",
                "priority": "medium"
            })
        
        return {
            "suggestions_generated": len(suggestions),
            "suggestions": suggestions,
        }
    
    def _store_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        tool_calls: Optional[List[Dict]] = None,
    ) -> int:
        """Store a message in the conversation history."""
        return execute_write("""
            INSERT INTO agent_conversations 
            (session_id, role, content, tool_calls, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            session_id,
            role,
            content,
            json.dumps(tool_calls) if tool_calls else None
        ))
    
    def _store_pending_action(self, session_id: str, action: Dict[str, Any]) -> int:
        """Store a pending action for approval."""
        return execute_write("""
            INSERT INTO agent_actions
            (session_id, action_type, action_params, status, requires_approval, created_at)
            VALUES (?, ?, ?, 'pending_approval', 1, CURRENT_TIMESTAMP)
        """, (
            session_id,
            action.get('tool_name', ''),
            json.dumps(action.get('parameters', {}))
        ))


# Singleton instance
_agent_service = None


def get_agent_service() -> AgentService:
    """Get the singleton agent service instance."""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
