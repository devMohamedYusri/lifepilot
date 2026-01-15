"""
Agent API Router

REST API endpoints for the autonomous agent.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

from models import (
    AgentChatRequest,
    AgentChatResponse,
    AgentConversationResponse,
    AgentAction,
    AgentActionApproval,
    AgentSettings,
    AgentStatus,
    AgentProactiveCheckResult,
)
from services.agent import get_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def chat(request: AgentChatRequest):
    """
    Send a message to the agent and get a response.
    
    If session_id is provided, continues existing conversation.
    If not provided, starts a new conversation.
    """
    agent = get_agent_service()
    
    try:
        result = agent.chat(
            message=request.message,
            session_id=request.session_id
        )
        
        # Convert pending actions to model
        pending_actions = [
            AgentAction(
                id=a.get('id'),
                action_type=a.get('tool_name', a.get('action_type', '')),
                action_params=a.get('parameters', a.get('action_params')),
                status=a.get('status', 'pending_approval'),
                requires_approval=True,
            )
            for a in result.get('pending_actions', [])
        ]
        
        return AgentChatResponse(
            session_id=result['session_id'],
            response=result['response'],
            pending_actions=pending_actions,
            suggestions=result.get('suggestions', []),
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def list_conversations(limit: int = 20):
    """List recent conversations with the agent."""
    agent = get_agent_service()
    return agent.get_conversations(limit=limit)


@router.get("/conversations/{session_id}", response_model=AgentConversationResponse)
async def get_conversation(session_id: str):
    """Get full conversation by session ID."""
    agent = get_agent_service()
    conversation = agent.get_conversation(session_id)
    
    if not conversation.get('messages'):
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return AgentConversationResponse(
        session_id=conversation['session_id'],
        messages=conversation['messages'],
        message_count=conversation['message_count'],
        created_at=conversation.get('created_at'),
        last_message_at=conversation.get('last_message_at'),
    )


@router.get("/pending-actions")
async def get_pending_actions():
    """Get all actions awaiting user approval."""
    agent = get_agent_service()
    actions = agent.get_pending_actions()
    
    return [
        AgentAction(
            id=a['id'],
            session_id=a.get('session_id'),
            action_type=a['action_type'],
            action_params=a.get('action_params'),
            status=a['status'],
            requires_approval=bool(a.get('requires_approval', 1)),
            created_at=a.get('created_at'),
        )
        for a in actions
    ]


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: int):
    """Approve and execute a pending action."""
    agent = get_agent_service()
    result = agent.approve_action(action_id)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Approval failed'))
    
    return result


@router.post("/actions/{action_id}/reject")
async def reject_action(action_id: int, feedback: Optional[str] = None):
    """Reject a pending action with optional feedback."""
    agent = get_agent_service()
    result = agent.reject_action(action_id, feedback)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Rejection failed'))
    
    return result


@router.get("/status", response_model=AgentStatus)
async def get_status():
    """Get current agent status and statistics."""
    agent = get_agent_service()
    status = agent.get_status()
    
    return AgentStatus(
        mode=status['mode'],
        is_active=status['is_active'],
        total_conversations=status['total_conversations'],
        total_actions_executed=status['total_actions_executed'],
        pending_actions=status['pending_actions'],
        memory_count=status['memory_count'],
        active_goals=status['active_goals'],
        last_activity_at=status.get('last_activity_at'),
    )


@router.get("/settings", response_model=AgentSettings)
async def get_settings():
    """Get current agent settings."""
    agent = get_agent_service()
    settings = agent.get_settings()
    
    return AgentSettings(
        agent_mode=settings.get('agent_mode', 'assistant'),
        auto_approve_safe_actions=settings.get('auto_approve_safe_actions', True),
        max_actions_per_turn=settings.get('max_actions_per_turn', 5),
        max_autonomous_actions_per_hour=settings.get('max_autonomous_actions_per_hour', 10),
        proactive_check_interval_minutes=settings.get('proactive_check_interval_minutes', 30),
        enable_memory_learning=settings.get('enable_memory_learning', True),
        confidence_threshold_high=settings.get('confidence_threshold_high', 0.8),
        confidence_threshold_medium=settings.get('confidence_threshold_medium', 0.5),
    )


@router.put("/settings", response_model=AgentSettings)
async def update_settings(settings: AgentSettings):
    """Update agent settings."""
    agent = get_agent_service()
    
    updates = settings.model_dump()
    updated = agent.update_settings(updates)
    
    return AgentSettings(
        agent_mode=updated.get('agent_mode', 'assistant'),
        auto_approve_safe_actions=updated.get('auto_approve_safe_actions', True),
        max_actions_per_turn=updated.get('max_actions_per_turn', 5),
        max_autonomous_actions_per_hour=updated.get('max_autonomous_actions_per_hour', 10),
        proactive_check_interval_minutes=updated.get('proactive_check_interval_minutes', 30),
        enable_memory_learning=updated.get('enable_memory_learning', True),
        confidence_threshold_high=updated.get('confidence_threshold_high', 0.8),
        confidence_threshold_medium=updated.get('confidence_threshold_medium', 0.5),
    )


@router.post("/proactive-check", response_model=AgentProactiveCheckResult)
async def run_proactive_check():
    """
    Trigger a proactive analysis.
    
    This checks for situations that might need the user's attention
    and generates suggestions if appropriate.
    """
    agent = get_agent_service()
    result = agent.run_proactive_check()
    
    return AgentProactiveCheckResult(
        suggestions_generated=result.get('suggestions_generated', 0),
        notifications_created=0,  # TODO: Integrate with notification system
        insights=[s.get('message', '') for s in result.get('suggestions', [])],
    )
