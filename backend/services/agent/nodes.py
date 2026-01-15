"""
Agent Graph Nodes

Implements each node in the agent's LangGraph workflow.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.groq_service import call_groq
from core.config import settings
from .state import AgentState, RecommendedAction, ToolCall
from .prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    CONTEXT_ANALYSIS_PROMPT,
    ACTION_PLANNING_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    REFLECTION_PROMPT,
)
from .tools import get_tool_registry
from .memory import get_memory_manager
from database import execute_query

logger = logging.getLogger(__name__)


def classify_intent(state: AgentState) -> AgentState:
    """
    Classify the user's intent and extract entities.
    Uses the fast model for quick classification.
    """
    user_message = state.get("user_message", "")
    
    try:
        prompt = INTENT_CLASSIFICATION_PROMPT.format(user_message=user_message)
        
        response = call_groq(
            prompt=prompt,
            model=settings.ai_model_fast,
            temperature=0.1,
            max_tokens=512
        )
        
        # Parse JSON response
        try:
            # Clean up response - sometimes LLM adds extra text
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                response = response[json_start:json_end]
            
            result = json.loads(response)
            
            return {
                **state,
                "intent": result.get("intent", "chat"),
                "entities": result.get("entities", {}),
                "confidence": result.get("confidence", 0.5),
            }
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse intent classification: {response}")
            return {
                **state,
                "intent": "chat",
                "entities": {},
                "confidence": 0.3,
            }
            
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return {
            **state,
            "intent": "chat",
            "entities": {},
            "confidence": 0.0,
            "error": f"Classification failed: {str(e)}"
        }


def gather_context(state: AgentState) -> AgentState:
    """
    Gather relevant context from LifePilot based on intent.
    """
    intent = state.get("intent", "")
    entities = state.get("entities", {})
    
    context = {}
    
    try:
        # Always get basic stats
        context["items_summary"] = _get_items_summary()
        
        # Get context based on intent
        if intent in ["question", "request", "task"]:
            # Get active items
            context["active_items"] = execute_query("""
                SELECT id, raw_content, type, priority, due_date, ai_summary
                FROM items WHERE status = 'active'
                AND (snoozed_until IS NULL OR snoozed_until <= date('now'))
                ORDER BY priority DESC, due_date ASC
                LIMIT 10
            """)
            
            # Check for mentioned contacts
            if entities.get("contacts"):
                for contact_name in entities["contacts"]:
                    contacts = execute_query("""
                        SELECT * FROM contacts 
                        WHERE name LIKE ? OR nickname LIKE ?
                        LIMIT 5
                    """, (f"%{contact_name}%", f"%{contact_name}%"))
                    context.setdefault("related_contacts", []).extend(contacts)
            
            # Check for date-related queries
            if entities.get("dates") or "today" in state.get("user_message", "").lower():
                today = datetime.now().strftime("%Y-%m-%d")
                context["todays_events"] = execute_query("""
                    SELECT * FROM calendar_events
                    WHERE date(start_time) = ?
                    ORDER BY start_time
                """, (today,))
        
        # Get recent patterns if asking about productivity
        if any(word in state.get("user_message", "").lower() 
               for word in ["pattern", "productive", "energy", "focus"]):
            context["patterns"] = execute_query("""
                SELECT * FROM patterns 
                WHERE is_active = 1 
                ORDER BY confidence DESC 
                LIMIT 5
            """)
        
        # Get memories
        memory_manager = get_memory_manager()
        memory_context = memory_manager.get_context_for_conversation(
            state.get("user_message", "")
        )
        
        return {
            **state,
            "context": context,
            "memories": memory_context.get("preferences", []) + memory_context.get("facts", []),
        }
        
    except Exception as e:
        logger.error(f"Context gathering failed: {e}")
        return {
            **state,
            "context": {},
            "memories": [],
            "error": f"Context gathering failed: {str(e)}"
        }


def reason_and_plan(state: AgentState) -> AgentState:
    """
    Analyze the situation and plan actions.
    Uses the smart model for complex reasoning.
    """
    user_message = state.get("user_message", "")
    intent = state.get("intent", "")
    confidence = state.get("confidence", 0.0)
    context = state.get("context", {})
    
    tool_registry = get_tool_registry()
    
    try:
        # Build context summary for prompt
        context_summary = _build_context_summary(context)
        available_tools = tool_registry.get_tools_description()
        
        prompt = ACTION_PLANNING_PROMPT.format(
            user_message=user_message,
            intent=intent,
            confidence=confidence,
            context_summary=context_summary,
            available_tools=available_tools
        )
        
        response = call_groq(
            prompt=prompt,
            model=settings.ai_model_smart,
            temperature=0.2,
            max_tokens=1024
        )
        
        # Parse JSON response
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                response = response[json_start:json_end]
            
            result = json.loads(response)
            
            # Convert to tool calls
            tool_calls = []
            pending_approvals = []
            
            for action in result.get("recommended_actions", []):
                tool = tool_registry.get_tool(action.get("action_type", ""))
                
                tool_call = {
                    "tool_name": action.get("action_type"),
                    "parameters": action.get("parameters", {}),
                    "reasoning": action.get("reasoning", ""),
                    "confidence": action.get("confidence", 0.5),
                    "requires_approval": action.get("requires_approval", True) or (tool and tool.requires_approval),
                    "status": "planned"
                }
                
                if tool_call["requires_approval"]:
                    pending_approvals.append(tool_call)
                else:
                    tool_calls.append(tool_call)
            
            return {
                **state,
                "analysis": result.get("analysis", ""),
                "recommended_actions": result.get("recommended_actions", []),
                "risks": result.get("risks", []),
                "tool_calls": tool_calls,
                "pending_approvals": pending_approvals,
                "should_interrupt": len(pending_approvals) > 0,
            }
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse action planning: {response}")
            return {
                **state,
                "analysis": response,
                "recommended_actions": [],
                "tool_calls": [],
                "pending_approvals": [],
            }
            
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        return {
            **state,
            "error": f"Reasoning failed: {str(e)}"
        }


async def execute_actions(state: AgentState) -> AgentState:
    """
    Execute approved tool calls.
    """
    tool_calls = state.get("tool_calls", [])
    tool_registry = get_tool_registry()
    
    results = []
    
    for tool_call in tool_calls:
        if tool_call.get("status") == "planned":
            tool_name = tool_call.get("tool_name")
            parameters = tool_call.get("parameters", {})
            
            try:
                result = await tool_registry.execute_tool(tool_name, parameters)
                
                results.append({
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "result": result,
                    "status": "completed" if result.get("success") else "failed",
                    "error": result.get("error")
                })
                
            except Exception as e:
                logger.error(f"Tool execution failed for {tool_name}: {e}")
                results.append({
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "status": "failed",
                    "error": str(e)
                })
    
    return {
        **state,
        "tool_results": results,
    }


def execute_actions_sync(state: AgentState) -> AgentState:
    """
    Synchronous version of execute_actions for graph compatibility.
    """
    tool_calls = state.get("tool_calls", [])
    tool_registry = get_tool_registry()
    
    results = []
    
    for tool_call in tool_calls:
        if tool_call.get("status") == "planned":
            tool_name = tool_call.get("tool_name")
            parameters = tool_call.get("parameters", {})
            
            try:
                # Get the tool and call it directly (sync)
                tool = tool_registry.get_tool(tool_name)
                if tool:
                    result = tool.function(parameters)
                    results.append({
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "result": {"success": True, "result": result},
                        "status": "completed"
                    })
                else:
                    results.append({
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "status": "failed",
                        "error": f"Unknown tool: {tool_name}"
                    })
                    
            except Exception as e:
                logger.error(f"Tool execution failed for {tool_name}: {e}")
                results.append({
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "status": "failed",
                    "error": str(e)
                })
    
    return {
        **state,
        "tool_results": results,
    }


def generate_response(state: AgentState) -> AgentState:
    """
    Generate the final response to send to the user.
    """
    user_message = state.get("user_message", "")
    intent = state.get("intent", "")
    context = state.get("context", {})
    tool_results = state.get("tool_results", [])
    pending_approvals = state.get("pending_approvals", [])
    
    try:
        context_summary = _build_context_summary(context)
        
        # Format actions taken
        actions_taken = ""
        for result in tool_results:
            status = "✓" if result.get("status") == "completed" else "✗"
            actions_taken += f"\n- {status} {result.get('tool_name')}: {json.dumps(result.get('result', {}))}"
        
        if not actions_taken:
            actions_taken = "No actions taken."
        
        # Format pending actions
        pending_str = ""
        for action in pending_approvals:
            pending_str += f"\n- {action.get('tool_name')}: {action.get('reasoning', 'No reason provided')}"
        
        if not pending_str:
            pending_str = "None"
        
        prompt = RESPONSE_GENERATION_PROMPT.format(
            user_message=user_message,
            intent=intent,
            context_summary=context_summary,
            actions_taken=actions_taken,
            pending_actions=pending_str
        )
        
        response = call_groq(
            prompt=prompt,
            model=settings.ai_model_smart,
            temperature=0.4,
            max_tokens=1024
        )
        
        # Extract follow-up suggestions if present
        suggestions = []
        if "suggestion" in response.lower() or "you could" in response.lower():
            # Simple extraction - could be more sophisticated
            suggestions = ["Let me know if you need anything else!"]
        
        return {
            **state,
            "response": response.strip(),
            "follow_up_suggestions": suggestions,
        }
        
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return {
            **state,
            "response": "I apologize, but I encountered an issue generating a response. Please try again.",
            "error": f"Response generation failed: {str(e)}"
        }


def reflect_and_learn(state: AgentState) -> AgentState:
    """
    Reflect on the interaction and extract learnings.
    """
    user_message = state.get("user_message", "")
    tool_results = state.get("tool_results", [])
    
    # Only reflect if there were actions
    if not tool_results:
        return state
    
    try:
        memory_manager = get_memory_manager()
        
        # Extract and store memories
        memories_stored = memory_manager.extract_memories_from_interaction(
            user_message=user_message,
            agent_response=state.get("response", ""),
            actions_taken=tool_results
        )
        
        logger.info(f"Stored {len(memories_stored)} memories from interaction")
        
        return state
        
    except Exception as e:
        logger.error(f"Reflection failed: {e}")
        return state


def should_execute(state: AgentState) -> str:
    """
    Conditional edge: decide whether to execute or interrupt for approval.
    """
    pending = state.get("pending_approvals", [])
    tool_calls = state.get("tool_calls", [])
    
    if pending and not tool_calls:
        # Only pending approvals, need human input
        return "interrupt"
    elif tool_calls:
        # Have approved actions to execute
        return "execute"
    else:
        # No actions, just respond
        return "respond"


def should_continue(state: AgentState) -> str:
    """
    Conditional edge: decide whether to reflect or just respond.
    """
    tool_results = state.get("tool_results", [])
    
    if tool_results:
        return "reflect"
    else:
        return "respond"


# Helper functions

def _get_items_summary() -> Dict[str, int]:
    """Get summary counts of items."""
    result = execute_query("""
        SELECT 
            SUM(CASE WHEN status = 'inbox' THEN 1 ELSE 0 END) as inbox,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN status = 'done' AND date(updated_at) = date('now') THEN 1 ELSE 0 END) as done_today,
            SUM(CASE WHEN due_date IS NOT NULL AND due_date < date('now') AND status = 'active' THEN 1 ELSE 0 END) as overdue
        FROM items
    """)
    
    if result:
        return dict(result[0])
    return {"inbox": 0, "active": 0, "done_today": 0, "overdue": 0}


def _build_context_summary(context: Dict[str, Any]) -> str:
    """Build a readable summary of context for the LLM."""
    parts = []
    
    if context.get("items_summary"):
        summary = context["items_summary"]
        parts.append(f"Items: {summary.get('active', 0)} active, {summary.get('inbox', 0)} in inbox, {summary.get('overdue', 0)} overdue")
    
    if context.get("active_items"):
        items = context["active_items"][:5]
        items_str = "\n".join([f"  - [{i.get('type')}] {i.get('raw_content', '')[:50]}..." for i in items])
        parts.append(f"Top active items:\n{items_str}")
    
    if context.get("todays_events"):
        events = context["todays_events"]
        events_str = "\n".join([f"  - {e.get('start_time', '')}: {e.get('title', '')}" for e in events])
        parts.append(f"Today's events:\n{events_str}")
    
    if context.get("related_contacts"):
        contacts = context["related_contacts"]
        contacts_str = ", ".join([c.get('name', '') for c in contacts])
        parts.append(f"Related contacts: {contacts_str}")
    
    if context.get("patterns"):
        patterns = context["patterns"][:3]
        patterns_str = "\n".join([f"  - {p.get('description', '')}" for p in patterns])
        parts.append(f"Known patterns:\n{patterns_str}")
    
    return "\n\n".join(parts) if parts else "No relevant context available."
