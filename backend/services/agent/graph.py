"""
Agent Graph Definition

Builds the LangGraph state machine for the autonomous agent.
"""

import logging
from typing import Dict, Any, Optional, Literal

from langgraph.graph import StateGraph, END

from .state import AgentState, create_initial_state
from .nodes import (
    classify_intent,
    gather_context,
    reason_and_plan,
    execute_actions_sync,
    generate_response,
    reflect_and_learn,
    should_execute,
    should_continue,
)

logger = logging.getLogger(__name__)


def build_agent_graph() -> StateGraph:
    """
    Build the LangGraph for the autonomous agent.
    
    Graph structure:
    
    Entry -> Classify Intent -> Gather Context -> Reason & Plan
                                                       |
                                     +-----------------+-----------------+
                                     |                 |                 |
                                 [execute]        [interrupt]        [respond]
                                     |                 |                 |
                                 Execute           (return)         Generate
                                     |                               Response
                                     +------------+                     |
                                                  |                     |
                                              [reflect]              [done]
                                                  |                     |
                                               Reflect              (END)
                                                  |
                                              Generate
                                              Response
                                                  |
                                                (END)
    """
    
    # Create the graph with AgentState
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("gather_context", gather_context)
    workflow.add_node("reason_and_plan", reason_and_plan)
    workflow.add_node("execute_actions", execute_actions_sync)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("reflect_and_learn", reflect_and_learn)
    
    # Set entry point
    workflow.set_entry_point("classify_intent")
    
    # Add edges
    workflow.add_edge("classify_intent", "gather_context")
    workflow.add_edge("gather_context", "reason_and_plan")
    
    # Conditional edge after planning
    workflow.add_conditional_edges(
        "reason_and_plan",
        should_execute,
        {
            "execute": "execute_actions",
            "interrupt": "generate_response",  # Generate response asking for approval
            "respond": "generate_response",
        }
    )
    
    # Conditional edge after execution
    workflow.add_conditional_edges(
        "execute_actions",
        should_continue,
        {
            "reflect": "reflect_and_learn",
            "respond": "generate_response",
        }
    )
    
    # Final edges
    workflow.add_edge("reflect_and_learn", "generate_response")
    workflow.add_edge("generate_response", END)
    
    return workflow


def compile_agent_graph():
    """
    Compile the agent graph for execution.
    
    Returns a compiled graph that can be invoked with state.
    """
    workflow = build_agent_graph()
    
    # Compile without checkpointing for now (stateless per request)
    # For persistence, we'd add a checkpointer here
    compiled = workflow.compile()
    
    return compiled


# Singleton compiled graph
_compiled_graph = None


def get_compiled_graph():
    """Get the singleton compiled graph instance."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_agent_graph()
    return _compiled_graph


def run_agent(user_message: str, session_id: str) -> Dict[str, Any]:
    """
    Run the agent graph with a user message.
    
    Args:
        user_message: The user's message
        session_id: Session identifier for conversation tracking
        
    Returns:
        Final state dict with response and any pending actions
    """
    graph = get_compiled_graph()
    
    # Create initial state
    initial_state = create_initial_state(user_message, session_id)
    
    try:
        # Run the graph
        final_state = graph.invoke(initial_state)
        
        return {
            "success": True,
            "session_id": session_id,
            "response": final_state.get("response", ""),
            "intent": final_state.get("intent", ""),
            "pending_approvals": final_state.get("pending_approvals", []),
            "tool_results": final_state.get("tool_results", []),
            "suggestions": final_state.get("follow_up_suggestions", []),
            "error": final_state.get("error"),
        }
        
    except Exception as e:
        logger.error(f"Agent graph execution failed: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "response": "I apologize, but I encountered an error processing your request. Please try again.",
            "error": str(e),
        }
