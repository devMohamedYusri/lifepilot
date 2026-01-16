/**
 * Agent API
 */
import { request } from './core';

export const agentApi = {
    chat: (message, sessionId = null) => request('/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId })
    }),

    listConversations: (limit = 20) => request(`/agent/conversations?limit=${limit}`),

    getConversation: (sessionId) => request(`/agent/conversations/${sessionId}`),

    getPendingActions: () => request('/agent/pending-actions'),

    approveAction: (actionId) => request(`/agent/actions/${actionId}/approve`, {
        method: 'POST'
    }),

    rejectAction: (actionId, feedback = null) => request(`/agent/actions/${actionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback })
    }),

    getStatus: () => request('/agent/status'),

    getSettings: () => request('/agent/settings'),

    updateSettings: (settings) => request('/agent/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    })
};
