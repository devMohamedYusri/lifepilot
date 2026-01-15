"""
Agent Tools Registry

Maps agent capabilities to LifePilot's backend services.
Each tool is a function that can be invoked by the agent.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

# Import LifePilot services and database
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import execute_query, execute_write
from services.categorizer import categorize_input
from services.crm_service import (
    get_contact_suggestions,
    suggest_contact_details,
    calculate_next_contact
)
from services.energy_service import (
    get_today_logs,
    analyze_patterns as analyze_energy_patterns,
    get_best_time_for_task,
    calculate_averages,
    get_time_block
)
from services.decision_service import (
    expand_decision,
    generate_insights as generate_decision_insights
)
from services.search_service import perform_search
from services.review_service import generate_review
from services.notification_service import (
    get_pending_notifications,
    create_notification
)
from services.groq_service import call_groq
from services.bookmark_analyzer import (
    fetch_url_metadata,
    analyze_bookmark,
    generate_reading_queue
)

logger = logging.getLogger(__name__)

# =============================================================================
# PROMPTS FOR ANALYSIS TOOLS
# =============================================================================

ANALYZE_SITUATION_PROMPT = """Analyze this situation and provide recommendations. Return ONLY valid JSON.

Situation: "{context}"

Provide:
1. Analysis of key factors
2. 3 potential actions with pros/cons
3. Recommended validation steps

Return format:
{{
  "analysis": "The situation involves...",
  "options": [
    {{"action": "Do X", "pros": ["Quick"], "cons": ["Risky"]}}
  ],
  "recommendation": "Option 1 is best because..."
}}"""

SUMMARIZE_DATA_PROMPT = """Summarize this data. Return ONLY valid JSON.

Data Type: {data_type}
Data: {data}

Return format:
{{
  "summary": "Key points are...",
  "trends": ["Trend A", "Trend B"],
  "outliers": ["Point C is unusual"]
}}"""

COMPARE_OPTIONS_PROMPT = """Compare these options. Return ONLY valid JSON.

Options: {options}

Compare based on: feasibility, impact, cost, risk.

Return format:
{{
  "comparison": [
    {{"option": "A", "feasibility": "high", "impact": "medium", "score": 8, "reasoning": "..."}}
  ],
  "winner": "Option A"
}}"""


@dataclass
class Tool:
    """Definition of an agent tool."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    requires_approval: bool
    category: str
    function: Callable


class ToolRegistry:
    """Registry of all available agent tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all available tools."""
        
        # =========================================================================
        # ITEMS TOOLS
        # =========================================================================
        
        self.register(Tool(
            name="create_item",
            description="Create a new item (task, note, decision, etc.) with optional details",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The item content/description"},
                    "item_type": {"type": "string", "enum": ["task", "waiting_for", "decision", "note", "life_admin"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                    "context": {"type": "string", "description": "Context tags (e.g. @computer, @calls)"}
                },
                "required": ["content"]
            },
            requires_approval=False,
            category="items",
            function=self._create_item
        ))
        
        self.register(Tool(
            name="list_items",
            description="List items with optional filters",
            parameters={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["inbox", "active", "done", "archived"]},
                    "type": {"type": "string", "enum": ["task", "waiting_for", "decision", "note", "life_admin"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "limit": {"type": "integer", "default": 20}
                }
            },
            requires_approval=False,
            category="items",
            function=self._list_items
        ))

        self.register(Tool(
            name="get_item",
            description="Get detailed information about a specific item",
            parameters={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"}
                },
                "required": ["item_id"]
            },
            requires_approval=False,
            category="items",
            function=self._get_item
        ))
        
        self.register(Tool(
            name="update_item",
            description="Update fields of an existing item",
            parameters={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                    "updates": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            "due_date": {"type": "string"},
                            "context": {"type": "string"}
                        }
                    }
                },
                "required": ["item_id", "updates"]
            },
            requires_approval=False,
            category="items",
            function=self._update_item
        ))
        
        self.register(Tool(
            name="complete_item",
            description="Mark an item as done",
            parameters={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"}
                },
                "required": ["item_id"]
            },
            requires_approval=False,
            category="items",
            function=self._mark_item_done
        ))
        
        self.register(Tool(
            name="snooze_item",
            description="Snooze an item until a later date",
            parameters={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                    "snooze_until": {"type": "string", "description": "Date to snooze until (YYYY-MM-DD)"}
                },
                "required": ["item_id", "snooze_until"]
            },
            requires_approval=False,
            category="items",
            function=self._snooze_item
        ))
        
        self.register(Tool(
            name="delete_item",
            description="Permanently delete an item",
            parameters={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"}
                },
                "required": ["item_id"]
            },
            requires_approval=True,
            category="items",
            function=self._delete_item
        ))
        
        self.register(Tool(
            name="get_today_focus",
            description="Get AI-recommended focus items for today",
            parameters={
                "type": "object", 
                "properties": {
                     "energy_level": {"type": "string", "enum": ["high", "medium", "low"]}
                }
            },
            requires_approval=False,
            category="items",
            function=self._get_today_focus
        ))

        self.register(Tool(
            name="follow_up_item",
            description="Record a follow-up action on a waiting-for item",
            parameters={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                    "note": {"type": "string", "description": "Optional note about the follow-up"}
                },
                "required": ["item_id"]
            },
            requires_approval=False,
            category="items",
            function=self._follow_up_item
        ))
        
        # =========================================================================
        # BOOKMARKS TOOLS
        # =========================================================================
        
        self.register(Tool(
            name="create_bookmark",
            description="Save a new bookmark/URL",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "notes": {"type": "string"},
                    "source": {"type": "string"}
                },
                "required": ["url"]
            },
            requires_approval=False,
            category="bookmarks",
            function=self._create_bookmark
        ))
        
        self.register(Tool(
            name="list_bookmarks",
            description="List bookmarks with filters",
            parameters={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["unread", "in_progress", "completed"]},
                    "category": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                }
            },
            requires_approval=False,
            category="bookmarks",
            function=self._list_bookmarks
        ))
        
        self.register(Tool(
            name="get_reading_queue",
            description="Get recommended reading based on available time and energy",
            parameters={
                "type": "object",
                "properties": {
                    "minutes": {"type": "integer", "default": 30},
                    "energy": {"type": "string", "enum": ["high", "medium", "low"]}
                }
            },
            requires_approval=False,
            category="bookmarks",
            function=self._get_reading_queue
        ))
        
        self.register(Tool(
            name="start_reading",
            description="Mark a bookmark as in-progress (start reading session)",
            parameters={
                "type": "object",
                "properties": {
                    "bookmark_id": {"type": "integer"}
                },
                "required": ["bookmark_id"]
            },
            requires_approval=False,
            category="bookmarks",
            function=self._start_reading
        ))

        self.register(Tool(
            name="complete_bookmark",
            description="Mark a bookmark as completed",
            parameters={
                "type": "object",
                "properties": {
                    "bookmark_id": {"type": "integer"}
                },
                "required": ["bookmark_id"]
            },
            requires_approval=False,
            category="bookmarks",
            function=self._complete_bookmark
        ))
        
        # =========================================================================
        # CONTACTS TOOLS
        # =========================================================================
        
        self.register(Tool(
            name="create_contact",
            description="Create a new contact",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "relationship_type": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["name"]
            },
            requires_approval=False,
            category="contacts",
            function=self._create_contact
        ))
        
        self.register(Tool(
            name="list_contacts",
            description="List contacts with filters",
            parameters={
                "type": "object",
                "properties": {
                    "search": {"type": "string"},
                    "needs_attention": {"type": "boolean"},
                    "limit": {"type": "integer", "default": 10}
                }
            },
            requires_approval=False,
            category="contacts",
            function=self._list_contacts
        ))
        
        self.register(Tool(
            name="get_contact",
            description="Get detailed contact info including interaction history",
            parameters={
                "type": "object",
                "properties": {
                    "contact_id": {"type": "integer"}
                },
                "required": ["contact_id"]
            },
            requires_approval=False,
            category="contacts",
            function=self._get_contact
        ))
        
        self.register(Tool(
            name="update_contact",
            description="Update contact information",
            parameters={
                "type": "object",
                "properties": {
                    "contact_id": {"type": "integer"},
                    "updates": {"type": "object"}
                },
                "required": ["contact_id", "updates"]
            },
            requires_approval=False,
            category="contacts",
            function=self._update_contact
        ))
        
        self.register(Tool(
            name="log_interaction",
            description="Log an interaction with a contact",
            parameters={
                "type": "object",
                "properties": {
                    "contact_id": {"type": "integer"},
                    "interaction_type": {"type": "string", "enum": ["call", "message", "email", "meeting", "social", "other"]},
                    "summary": {"type": "string"},
                    "date": {"type": "string"}
                },
                "required": ["contact_id", "interaction_type"]
            },
            requires_approval=True,
            category="contacts",
            function=self._log_interaction
        ))
        
        self.register(Tool(
            name="get_contact_suggestions",
            description="Get AI suggestions for who to contact",
            parameters={"type": "object", "properties": {}},
            requires_approval=False,
            category="contacts",
            function=self._get_contact_suggestions
        ))
        
        # =========================================================================
        # DECISIONS TOOLS
        # =========================================================================
        
        self.register(Tool(
            name="list_decisions",
            description="List pending decisions",
            parameters={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["deliberating", "decided", "awaiting_outcome", "completed"]}
                }
            },
            requires_approval=False,
            category="decisions",
            function=self._list_decisions
        ))
        
        self.register(Tool(
            name="expand_decision",
            description="Analyze a decision and generate options using AI",
            parameters={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer", "description": "ID of the decision item"}
                },
                "required": ["item_id"]
            },
            requires_approval=False,
            category="decisions",
            function=self._expand_decision
        ))
        
        self.register(Tool(
            name="record_decision",
            description="Record the choice made for a decision",
            parameters={
                "type": "object",
                "properties": {
                    "decision_id": {"type": "integer"},
                    "chosen_option": {"type": "string"},
                    "reasoning": {"type": "string"},
                    "expected_outcome": {"type": "string"}
                },
                "required": ["decision_id", "chosen_option"]
            },
            requires_approval=False,
            category="decisions",
            function=self._record_decision
        ))
        
        self.register(Tool(
            name="record_outcome",
            description="Record the actual outcome of a decision",
            parameters={
                "type": "object",
                "properties": {
                    "decision_id": {"type": "integer"},
                    "actual_outcome": {"type": "string"},
                    "rating": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                    "lessons": {"type": "string"}
                },
                "required": ["decision_id", "actual_outcome", "rating"]
            },
            requires_approval=False,
            category="decisions",
            function=self._record_outcome
        ))
        
        self.register(Tool(
            name="get_decision_insights",
            description="Get insights from past decision patterns",
            parameters={"type": "object", "properties": {}},
            requires_approval=False,
            category="decisions",
            function=self._get_decision_insights
        ))

        # =========================================================================
        # ENERGY TOOLS
        # =========================================================================
        
        self.register(Tool(
            name="log_energy",
            description="Log current energy and focus levels",
            parameters={
                "type": "object",
                "properties": {
                    "energy_level": {"type": "integer", "minimum": 1, "maximum": 10},
                    "focus_level": {"type": "integer", "minimum": 1, "maximum": 10},
                    "mood_level": {"type": "integer", "minimum": 1, "maximum": 10},
                    "notes": {"type": "string"}
                },
                "required": ["energy_level"]
            },
            requires_approval=False,
            category="energy",
            function=self._log_energy
        ))

        self.register(Tool(
            name="get_energy_status",
            description="Get today's energy logs and summary",
            parameters={"type": "object", "properties": {}},
            requires_approval=False,
            category="energy",
            function=self._get_energy_status
        ))
        
        self.register(Tool(
            name="get_energy_patterns",
            description="Get AI analysis of energy patterns",
            parameters={"type": "object", "properties": {}},
            requires_approval=False,
            category="energy",
            function=self._get_energy_patterns
        ))
        
        self.register(Tool(
            name="get_best_time",
            description="Get best time for a specific type of work",
            parameters={
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "enum": ["deep_work", "meetings", "creative", "admin"]}
                },
                "required": ["task_type"]
            },
            requires_approval=False,
            category="energy",
            function=self._get_best_time
        ))

        # =========================================================================
        # CALENDAR TOOLS
        # =========================================================================
        
        self.register(Tool(
            name="get_calendar_events",
            description="Get calendar events for a date range",
            parameters={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "limit": {"type": "integer", "default": 20}
                }
            },
            requires_approval=False,
            category="calendar",
            function=self._get_calendar_events
        ))
        
        self.register(Tool(
            name="get_free_time",
            description="Find free time blocks",
            parameters={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "min_duration_minutes": {"type": "integer", "default": 30}
                }
            },
            requires_approval=False,
            category="calendar",
            function=self._get_free_time
        ))

        self.register(Tool(
            name="create_calendar_event",
            description="Create a calendar event",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO format"},
                    "end_time": {"type": "string", "description": "ISO format"},
                    "description": {"type": "string"}
                },
                "required": ["title", "start_time", "end_time"]
            },
            requires_approval=True,
            category="calendar",
            function=self._create_calendar_event
        ))

        self.register(Tool(
            name="update_calendar_event",
            description="Update a calendar event",
            parameters={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer"},
                    "updates": {"type": "object"}
                },
                "required": ["event_id", "updates"]
            },
            requires_approval=True,
            category="calendar",
            function=self._update_calendar_event
        ))

        # =========================================================================
        # SEARCH TOOLS
        # =========================================================================
        
        self.register(Tool(
            name="search_everything",
            description="Search across all data (items, bookmarks, decisions)",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "types": {
                        "type": "array", 
                        "items": {"type": "string", "enum": ["items", "bookmarks", "decisions"]},
                        "description": "Optional list of types to search"
                    },
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            },
            requires_approval=False,
            category="search",
            function=self._search_everything
        ))

        self.register(Tool(
            name="search_items",
            description="Search items specifically",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "status": {"type": "string", "enum": ["inbox", "active", "done", "archived"]},
                    "type": {"type": "string", "enum": ["task", "waiting_for", "decision", "note", "life_admin"]},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            },
            requires_approval=False,
            category="search",
            function=self._search_items
        ))

        self.register(Tool(
            name="search_bookmarks",
            description="Search bookmarks specifically",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "status": {"type": "string", "enum": ["unread", "in_progress", "completed"]},
                    "category": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            },
            requires_approval=False,
            category="search",
            function=self._search_bookmarks
        ))

        self.register(Tool(
            name="search_contacts",
            description="Search contacts by name, company, notes",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            },
            requires_approval=False,
            category="search",
            function=self._search_contacts
        ))

        # =========================================================================
        # PATTERNS TOOLS
        # =========================================================================

        self.register(Tool(
            name="get_patterns",
            description="Get discovered patterns about user behavior",
            parameters={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["productivity", "energy", "social", "learning", "decisions"]},
                    "limit": {"type": "integer", "default": 5}
                }
            },
            requires_approval=False,
            category="patterns",
            function=self._get_patterns
        ))

        self.register(Tool(
            name="get_insights",
            description="Get current active insights and recommendations",
            parameters={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["new", "seen", "dismissed"]}
                }
            },
            requires_approval=False,
            category="patterns",
            function=self._get_insights
        ))

        # =========================================================================
        # REVIEW TOOLS
        # =========================================================================
        
        self.register(Tool(
            name="get_weekly_review",
            description="Get or generate this week's review",
            parameters={
                "type": "object",
                "properties": {
                    "offset_weeks": {"type": "integer", "default": 0, "description": "0 for current week, -1 for last week"}
                }
            },
            requires_approval=False,
            category="review",
            function=self._get_weekly_review
        ))

        # =========================================================================
        # NOTIFICATION TOOLS
        # =========================================================================

        self.register(Tool(
            name="get_pending_notifications",
            description="Get notifications awaiting attention",
            parameters={"type": "object", "properties": {}},
            requires_approval=False,
            category="notifications",
            function=self._get_notifications
        ))

        self.register(Tool(
            name="create_reminder",
            description="Create a reminder notification",
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "remind_at": {"type": "string", "description": "ISO datetime"}
                },
                "required": ["message", "remind_at"]
            },
            requires_approval=False,
            category="notifications",
            function=self._create_reminder
        ))
        
        self.register(Tool(
            name="dismiss_notification",
            description="Dismiss a notification",
            parameters={
                "type": "object",
                "properties": {
                    "notification_id": {"type": "integer"}
                },
                "required": ["notification_id"]
            },
            requires_approval=False,
            category="notifications",
            function=self._dismiss_notification
        ))

        # =========================================================================
        # ANALYSIS TOOLS
        # =========================================================================

        self.register(Tool(
            name="analyze_situation",
            description="AI analysis of a situation or context",
            parameters={
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "Description of the situation"}
                },
                "required": ["context"]
            },
            requires_approval=False,
            category="analysis",
            function=self._analyze_situation
        ))

        self.register(Tool(
            name="summarize_data",
            description="Generate a natural language summary of data",
            parameters={
                "type": "object",
                "properties": {
                    "data_type": {"type": "string"},
                    "data": {"type": "string", "description": "JSON string or text representation of data"},
                    "time_range": {"type": "string"}
                },
                "required": ["data_type", "data"]
            },
            requires_approval=False,
            category="analysis",
            function=self._summarize_data
        ))

        self.register(Tool(
            name="compare_options",
            description="Compare multiple options using AI",
            parameters={
                "type": "object",
                "properties": {
                    "options": {"type": "string", "description": "List of options descriptions"}
                },
                "required": ["options"]
            },
            requires_approval=False,
            category="analysis",
            function=self._compare_options
        ))

    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())
    
    def get_tools_description(self) -> str:
        """Get a formatted description of all tools for the LLM."""
        descriptions = []
        for tool in self.tools.values():
            approval = " [REQUIRES APPROVAL]" if tool.requires_approval else ""
            desc = f"- {tool.name}: {tool.description}{approval}"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        try:
            # Sync wrapper for async safety if needed, though most are sync
            result = tool.function(parameters)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}\nParams: {parameters}")
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # TOOL IMPLEMENTATIONS
    # =========================================================================
    
    # --- ITEMS ---
    
    def _create_item(self, params: Dict[str, Any]) -> Dict:
        content = params.get("content", "")
        item_type = params.get("item_type")  # Let categorizer handle default if None
        priority = params.get("priority", "medium")
        due_date = params.get("due_date")
        context = params.get("context")
        
        # Use categorizer service logic
        if not item_type:
            cat_result = categorize_input(content)
            item_type = cat_result["type"]
            # Only override if not provided
            if not priority: priority = cat_result["priority"]
            if not due_date: due_date = cat_result["due_date"]
            if not context: context = cat_result["context"]

        item_id = execute_write("""
            INSERT INTO items (raw_content, type, status, priority, due_date, context, created_at, updated_at)
            VALUES (?, ?, 'active', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (content, item_type, priority, due_date, context))
        
        # If decision, create entry in decisions table
        if item_type == 'decision':
            execute_write("""
                INSERT INTO decisions (item_id, status, created_at)
                VALUES (?, 'deliberating', CURRENT_TIMESTAMP)
            """, (item_id,))
            
        return {"id": item_id, "status": "created", "type": item_type}

    def _list_items(self, params: Dict[str, Any]) -> List[Dict]:
        query = "SELECT * FROM items WHERE 1=1"
        qp = []
        
        if params.get("status"):
            query += " AND status = ?"
            qp.append(params["status"])
        else:
            query += " AND status != 'archived'" # Default to everything but archived if not specified
            
        if params.get("type"):
            query += " AND type = ?"
            qp.append(params["type"])
            
        if params.get("priority"):
            query += " AND priority = ?"
            qp.append(params["priority"])
            
        limit = params.get("limit", 20)
        query += " ORDER BY created_at DESC LIMIT ?"
        qp.append(limit)
        
        return execute_query(query, tuple(qp))

    def _get_item(self, params: Dict[str, Any]) -> Optional[Dict]:
        items = execute_query("SELECT * FROM items WHERE id = ?", (params["item_id"],))
        return items[0] if items else None

    def _update_item(self, params: Dict[str, Any]) -> Dict:
        item_id = params["item_id"]
        updates = params["updates"]
        
        fields = []
        values = []
        for k, v in updates.items():
            if k in ['content', 'priority', 'due_date', 'context', 'type', 'status']:
                fields.append(f"{k} = ?")
                values.append(v)
        
        if not fields:
            return {"error": "No valid fields to update"}
            
        values.append(item_id)
        query = f"UPDATE items SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        execute_write(query, tuple(values))
        return {"id": item_id, "status": "updated", "updates": updates}

    def _mark_item_done(self, params: Dict[str, Any]) -> Dict:
        item_id = params["item_id"]
        execute_write("UPDATE items SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
        return {"id": item_id, "status": "done"}

    def _snooze_item(self, params: Dict[str, Any]) -> Dict:
        item_id = params["item_id"]
        snooze_until = params["snooze_until"]
        execute_write("UPDATE items SET snoozed_until = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (snooze_until, item_id))
        return {"id": item_id, "snoozed_until": snooze_until}

    def _delete_item(self, params: Dict[str, Any]) -> Dict:
        item_id = params["item_id"]
        execute_write("DELETE FROM items WHERE id = ?", (item_id,))
        return {"id": item_id, "status": "deleted"}

    def _get_today_focus(self, params: Dict[str, Any]) -> Dict:
        energy = params.get("energy_level")
        query = """
            SELECT * FROM items 
            WHERE status = 'active' 
            AND (snoozed_until IS NULL OR snoozed_until <= date('now'))
        """
        qp = []
        
        if energy:
            # Map user energy to required energy: High energy -> High/Med/Low items. Low energy -> Low items.
            if energy == 'low':
                query += " AND energy_required = 'low'"
            elif energy == 'medium':
                query += " AND energy_required IN ('low', 'medium')"
            # High energy can do anything
            
        query += """
            ORDER BY 
                CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                due_date ASC NULLS LAST
            LIMIT 5
        """
        items = execute_query(query, tuple(qp))
        return {"focus_items": items}

    def _follow_up_item(self, params: Dict[str, Any]) -> Dict:
        item_id = params["item_id"]
        note = params.get("note", "")
        
        execute_write("""
            UPDATE items 
            SET follow_up_count = COALESCE(follow_up_count, 0) + 1,
                last_follow_up_note = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (note, item_id))
        
        return {"id": item_id, "status": "followed_up"}

    # --- BOOKMARKS ---

    def _create_bookmark(self, params: Dict[str, Any]) -> Dict:
        url = params["url"]
        meta = fetch_url_metadata(url)
        analysis = analyze_bookmark(url, meta.get("title"), meta.get("description"))
        
        bookmark_id = execute_write("""
            INSERT INTO bookmarks (url, title, description, category, topic_tags, 
                                 estimated_minutes, complexity, summary, key_takeaways, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unread', CURRENT_TIMESTAMP)
        """, (
            url, meta.get("title"), meta.get("description"),
            analysis.get("category"), json.dumps(analysis.get("topic_tags")),
            analysis.get("estimated_minutes"), analysis.get("complexity"),
            analysis.get("summary"), json.dumps(analysis.get("key_takeaways"))
        ))
        
        return {"id": bookmark_id, "status": "created", "analysis": analysis}

    def _list_bookmarks(self, params: Dict[str, Any]) -> List[Dict]:
        query = "SELECT * FROM bookmarks WHERE 1=1"
        qp = []
        
        if params.get("status"):
            query += " AND status = ?"
            qp.append(params["status"])
            
        if params.get("category"):
            query += " AND category = ?"
            qp.append(params["category"])
            
        limit = params.get("limit", 10)
        query += " ORDER BY created_at DESC LIMIT ?"
        qp.append(limit)
        
        return execute_query(query, tuple(qp))

    def _get_reading_queue(self, params: Dict[str, Any]) -> Dict:
        minutes = params.get("minutes", 30)
        energy = params.get("energy", "medium")
        
        bookmarks = execute_query("SELECT * FROM bookmarks WHERE status IN ('unread', 'in_progress') LIMIT 50")
        return generate_reading_queue(bookmarks, minutes, energy)

    def _start_reading(self, params: Dict[str, Any]) -> Dict:
        bid = params["bookmark_id"]
        execute_write("""
            UPDATE bookmarks SET status = 'in_progress', session_count = COALESCE(session_count, 0) + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (bid,))
        return {"id": bid, "status": "in_progress"}

    def _complete_bookmark(self, params: Dict[str, Any]) -> Dict:
        bid = params["bookmark_id"]
        execute_write("UPDATE bookmarks SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (bid,))
        return {"id": bid, "status": "completed"}

    # --- CONTACTS ---

    def _create_contact(self, params: Dict[str, Any]) -> Dict:
        cid = execute_write("""
            INSERT INTO contacts (name, relationship_type, email, phone, notes, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """, (params["name"], params.get("relationship_type"), params.get("email"), params.get("phone"), params.get("notes")))
        return {"id": cid, "status": "created"}

    def _list_contacts(self, params: Dict[str, Any]) -> List[Dict]:
        query = "SELECT * FROM contacts WHERE is_active = 1"
        qp = []
        if params.get("search"):
            query += " AND name LIKE ?"
            qp.append(f"%{params['search']}%")
        if params.get("needs_attention"):
             query += " AND (next_contact_date <= date('now') OR next_contact_date IS NULL)"
             
        limit = params.get("limit", 10)
        query += " ORDER BY name ASC LIMIT ?"
        qp.append(limit)
        return execute_query(query, tuple(qp))

    def _get_contact(self, params: Dict[str, Any]) -> Dict:
        cid = params["contact_id"]
        contacts = execute_query("SELECT * FROM contacts WHERE id = ?", (cid,))
        if not contacts:
            return {"error": "Contact not found"}
        
        interactions = execute_query("SELECT * FROM interactions WHERE contact_id = ? ORDER BY date DESC LIMIT 5", (cid,))
        contact = dict(contacts[0])
        contact["recent_interactions"] = [dict(i) for i in interactions]
        return contact

    def _update_contact(self, params: Dict[str, Any]) -> Dict:
        cid = params["contact_id"]
        updates = params["updates"]
        
        fields = []
        values = []
        for k, v in updates.items():
            if k in ['name', 'email', 'phone', 'relationship_type', 'notes']:
                fields.append(f"{k} = ?")
                values.append(v)
        
        if not fields:
            return {"error": "No valid fields"}
            
        values.append(cid)
        execute_write(f"UPDATE contacts SET {', '.join(fields)} WHERE id = ?", tuple(values))
        return {"id": cid, "status": "updated"}

    def _log_interaction(self, params: Dict[str, Any]) -> Dict:
        cid = params["contact_id"]
        itype = params["interaction_type"]
        summary = params.get("summary", "")
        date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        # Log interaction
        execute_write("INSERT INTO interactions (contact_id, type, date, summary, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                     (cid, itype, date, summary))
        
        # Update last contact date
        execute_write("UPDATE contacts SET last_contact_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (date, cid))
        
        # Calculate next contact (simple logic, assuming frequency exists or default 30)
        contact = execute_query("SELECT * FROM contacts WHERE id = ?", (cid,))[0]
        freq = contact.get("desired_frequency", "monthly")
        next_date = calculate_next_contact(date, freq)
        
        execute_write("UPDATE contacts SET next_contact_date = ? WHERE id = ?", (next_date, cid))
        
        return {"id": cid, "status": "interaction_logged", "next_contact": next_date}

    def _get_contact_suggestions(self, params: Dict[str, Any]) -> Dict:
        return get_contact_suggestions()

    # --- DECISIONS ---

    def _list_decisions(self, params: Dict[str, Any]) -> List[Dict]:
        query = """
            SELECT d.*, i.raw_content as title 
            FROM decisions d 
            JOIN items i ON d.item_id = i.id
            WHERE 1=1
        """
        qp = []
        if params.get("status"):
            query += " AND d.status = ?"
            qp.append(params["status"])
        else:
            query += " AND d.status != 'completed'"
            
        return execute_query(query, tuple(qp))

    def _expand_decision(self, params: Dict[str, Any]) -> Dict:
        item = execute_query("SELECT * FROM items WHERE id = ?", (params["item_id"],))
        if not item: return {"error": "Item not found"}
        
        expansion = expand_decision(item[0]["raw_content"])
        
        # Store analysis
        execute_write("""
            UPDATE decisions 
            SET context = ?, options = ?, stakeholders = ? 
            WHERE item_id = ?
        """, (
            expansion.get("situation"),
            json.dumps(expansion.get("options")),
            json.dumps(expansion.get("stakeholders")),
            params["item_id"]
        ))
        
        return expansion

    def _record_decision(self, params: Dict[str, Any]) -> Dict:
        execute_write("""
            UPDATE decisions 
            SET chosen_option = ?, reasoning = ?, expected_outcome = ?, status = 'decided', decided_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (params["chosen_option"], params.get("reasoning"), params.get("expected_outcome"), params["decision_id"]))
        return {"status": "decided"}

    def _record_outcome(self, params: Dict[str, Any]) -> Dict:
        execute_write("""
            UPDATE decisions 
            SET actual_outcome = ?, rating = ?, lessons = ?, status = 'completed'
            WHERE id = ?
        """, (params["actual_outcome"], params["rating"], params.get("lessons"), params["decision_id"]))
        return {"status": "completed"}

    def _get_decision_insights(self, params: Dict[str, Any]) -> Dict:
        decisions = execute_query("SELECT * FROM decisions WHERE status = 'completed' ORDER BY created_at DESC LIMIT 20")
        return generate_decision_insights(decisions)

    # --- ENERGY ---

    def _log_energy(self, params: Dict[str, Any]) -> Dict:
        block = get_time_block()
        execute_write("""
            INSERT INTO energy_logs (energy_level, focus_level, mood_level, notes, time_block, logged_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (params["energy_level"], params.get("focus_level"), params.get("mood_level"), params.get("notes"), block))
        return {"status": "logged"}

    def _get_energy_status(self, params: Dict[str, Any]) -> Dict:
        logs = get_today_logs()
        avgs = calculate_averages(logs)
        return {"todays_logs": [dict(l) for l in logs], "current_averages": avgs}

    def _get_energy_patterns(self, params: Dict[str, Any]) -> Dict:
        return analyze_energy_patterns()

    def _get_best_time(self, params: Dict[str, Any]) -> Dict:
        return get_best_time_for_task(params["task_type"])

    # --- CALENDAR ---

    def _get_calendar_events(self, params: Dict[str, Any]) -> List[Dict]:
        start = params.get("start_date", datetime.now().strftime("%Y-%m-%d"))
        end = params.get("end_date", (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))
        limit = params.get("limit", 20)
        
        return execute_query("""
            SELECT * FROM calendar_events 
            WHERE start_time >= ? AND start_time <= ?
            ORDER BY start_time ASC LIMIT ?
        """, (start, end, limit))

    def _get_free_time(self, params: Dict[str, Any]) -> List[Dict]:
        # Simple implementation: Look for gaps > min_minutes between 9am and 5pm
        date_str = params.get("date", datetime.now().strftime("%Y-%m-%d"))
        events = execute_query("SELECT start_time, end_time FROM calendar_events WHERE date(start_time) = ? ORDER BY start_time ASC", (date_str,))
        
        # This is a stub - real free time logic is complex. 
        # For now, return a placeholder or simple logic if events exist
        if not events:
            return [{"start": f"{date_str}T09:00:00", "end": f"{date_str}T17:00:00", "duration": 480}]
        
        return [{"message": "Complex free time calculation requires full calendar sync"}]

    def _create_calendar_event(self, params: Dict[str, Any]) -> Dict:
        # Create in local DB
        eid = execute_write("""
            INSERT INTO calendar_events (title, start_time, end_time, description, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (params["title"], params["start_time"], params["end_time"], params.get("description")))
        return {"id": eid, "status": "created_locally", "note": "Sync to external calendar happens in background"}

    def _update_calendar_event(self, params: Dict[str, Any]) -> Dict:
        eid = params["event_id"]
        updates = params["updates"]
        
        fields = []
        values = []
        for k, v in updates.items():
            if k in ['title', 'start_time', 'end_time', 'description']:
                fields.append(f"{k} = ?")
                values.append(v)
        
        if not fields:
            return {"error": "No valid fields"}
            
        values.append(eid)
        execute_write(f"UPDATE calendar_events SET {', '.join(fields)} WHERE id = ?", tuple(values))
        return {"id": eid, "status": "updated_locally"}

    # --- SEARCH & REVIEW & NOTIFICATIONS ---

    def _search_everything(self, params: Dict[str, Any]) -> Dict:
        # Pass types if provided, otherwise perform_search defaults to all
        return perform_search(params["query"], types=params.get("types"))

    def _search_items(self, params: Dict[str, Any]) -> List[Dict]:
        query = params["query"]
        search_term = f"%{query}%"
        sql = "SELECT * FROM items WHERE (raw_content LIKE ? OR ai_summary LIKE ? OR context LIKE ?)"
        qp = [search_term, search_term, search_term]
        
        if params.get("status"):
            sql += " AND status = ?"
            qp.append(params["status"])
        if params.get("type"):
            sql += " AND type = ?"
            qp.append(params["type"])
            
        sql += " ORDER BY created_at DESC LIMIT ?"
        qp.append(params.get("limit", 10))
        
        return execute_query(sql, tuple(qp))

    def _search_bookmarks(self, params: Dict[str, Any]) -> List[Dict]:
        query = params["query"]
        search_term = f"%{query}%"
        sql = "SELECT * FROM bookmarks WHERE (title LIKE ? OR description LIKE ? OR summary LIKE ? OR topic_tags LIKE ?)"
        qp = [search_term, search_term, search_term, search_term]
        
        if params.get("status"):
            sql += " AND status = ?"
            qp.append(params["status"])
        if params.get("category"):
            sql += " AND category = ?"
            qp.append(params["category"])
            
        sql += " ORDER BY created_at DESC LIMIT ?"
        qp.append(params.get("limit", 10))
        
        return execute_query(sql, tuple(qp))

    def _search_contacts(self, params: Dict[str, Any]) -> List[Dict]:
        query = params["query"]
        search_term = f"%{query}%"
        sql = "SELECT * FROM contacts WHERE (name LIKE ? OR company LIKE ? OR notes LIKE ? OR email LIKE ?) AND is_active = 1"
        qp = [search_term, search_term, search_term, search_term]
        sql += " ORDER BY name ASC LIMIT ?"
        qp.append(params.get("limit", 10))
        
        return execute_query(sql, tuple(qp))

    # --- PATTERNS ---

    def _get_patterns(self, params: Dict[str, Any]) -> List[Dict]:
        sql = "SELECT * FROM patterns WHERE is_active = 1"
        qp = []
        
        if params.get("category"):
            sql += " AND category = ?"
            qp.append(params["category"])
            
        sql += " ORDER BY confidence DESC LIMIT ?"
        qp.append(params.get("limit", 5))
        
        return execute_query(sql, tuple(qp))

    def _get_insights(self, params: Dict[str, Any]) -> List[Dict]:
        sql = "SELECT * FROM insights WHERE 1=1"
        qp = []
        
        if params.get("status"):
            sql += " AND status = ?"
            qp.append(params["status"])
        else:
            sql += " AND status IN ('new', 'seen')"
            
        sql += " ORDER BY priority DESC, created_at DESC LIMIT 10"
        
        return execute_query(sql, tuple(qp))

    def _get_weekly_review(self, params: Dict[str, Any]) -> Dict:
        return generate_review(params.get("offset_weeks", 0))

    def _get_notifications(self, params: Dict[str, Any]) -> List[Dict]:
        return get_pending_notifications()

    def _dismiss_notification(self, params: Dict[str, Any]) -> Dict:
        nid = params["notification_id"]
        execute_write("UPDATE notifications SET status = 'dismissed' WHERE id = ?", (nid,))
        return {"status": "dismissed"}

    def _create_reminder(self, params: Dict[str, Any]) -> Dict:
        create_notification(
            type="reminder",
            title="Reminder",
            message=params["message"],
            scheduled_for=params["remind_at"]
        )
        return {"status": "created"}

    # --- ANALYSIS ---

    def _analyze_situation(self, params: Dict[str, Any]) -> Dict:
        prompt = ANALYZE_SITUATION_PROMPT.format(context=params["context"])
        response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.5)
        try:
            return json.loads(response) 
        except:
            return {"analysis": response}

    def _summarize_data(self, params: Dict[str, Any]) -> Dict:
        prompt = SUMMARIZE_DATA_PROMPT.format(
            data_type=params["data_type"],
            data=params["data"]
        )
        response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.3)
        try:
            return json.loads(response)
        except:
            return {"summary": response}

    def _compare_options(self, params: Dict[str, Any]) -> Dict:
        prompt = COMPARE_OPTIONS_PROMPT.format(options=params["options"])
        response = call_groq(prompt, model="llama-3.3-70b-versatile", temperature=0.4)
        try:
            return json.loads(response)
        except:
            return {"comparison": response}


# Singleton instance
_tool_registry = None

def get_tool_registry() -> ToolRegistry:
    """Get the singleton tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
