"""
Agent State Definition

Defines the TypedDict used by LangGraph to maintain state
across graph node executions.
"""

from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass, field


class AgentState(TypedDict, total=False):
    """
    State passed through the agent graph.
    
    This state is updated by each node and passed to the next.
    All fields are optional to allow incremental updates.
    """
    
    # === Input ===
    user_message: str  # The user's input message
    session_id: str  # Conversation session identifier
    
    # === Classification ===
    intent: str  # question, request, task, chat, feedback
    entities: Dict[str, Any]  # Extracted entities (items, contacts, dates, etc.)
    confidence: float  # Classification confidence
    
    # === Context ===
    context: Dict[str, Any]  # Retrieved LifePilot data
    memories: List[Dict[str, Any]]  # Relevant memories from long-term storage
    
    # === Reasoning ===
    analysis: str  # Situation analysis text
    recommended_actions: List[Dict[str, Any]]  # Planned actions with reasoning
    risks: List[str]  # Identified risks/concerns
    
    # === Execution ===
    tool_calls: List[Dict[str, Any]]  # Planned tool invocations
    tool_results: List[Dict[str, Any]]  # Results from executed tools
    pending_approvals: List[Dict[str, Any]]  # Actions awaiting user approval
    
    # === Response ===
    response: str  # Final response to user
    follow_up_suggestions: List[str]  # Suggested next steps
    
    # === LLM Messages ===
    messages: List[Dict[str, Any]]  # Full conversation history for LLM
    
    # === Meta ===
    error: Optional[str]  # Error message if something failed
    should_interrupt: bool  # Flag to interrupt for human approval


@dataclass
class ToolCall:
    """Represents a planned tool invocation."""
    tool_name: str
    parameters: Dict[str, Any]
    requires_approval: bool = False
    reasoning: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    status: str = "planned"  # planned, approved, executing, completed, failed


@dataclass 
class RecommendedAction:
    """A recommended action from the reasoning node."""
    action_type: str
    description: str
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    requires_approval: bool = False


def create_initial_state(user_message: str, session_id: str) -> AgentState:
    """Create a fresh agent state for a new interaction."""
    return AgentState(
        user_message=user_message,
        session_id=session_id,
        intent="",
        entities={},
        confidence=0.0,
        context={},
        memories=[],
        analysis="",
        recommended_actions=[],
        risks=[],
        tool_calls=[],
        tool_results=[],
        pending_approvals=[],
        response="",
        follow_up_suggestions=[],
        messages=[],
        error=None,
        should_interrupt=False,
    )
