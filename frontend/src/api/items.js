/**
 * Items API
 */
import { request } from './core';

export const itemsApi = {
    create: (content) =>
        request('/items', {
            method: 'POST',
            body: JSON.stringify({ content }),
        }),

    list: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.type) params.set('type', filters.type);
        if (filters.status) params.set('status', filters.status);
        if (filters.include_snoozed) params.set('include_snoozed', 'true');
        const query = params.toString();
        return request(`/items${query ? `?${query}` : ''}`);
    },

    update: (id, data) =>
        request(`/items/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    delete: (id) =>
        request(`/items/${id}`, { method: 'DELETE' }),

    // Phase 2: Follow-up endpoints
    needsFollowup: () => request('/items/needs-followup'),

    followUp: (id, note = null) =>
        request(`/items/${id}/follow-up`, {
            method: 'POST',
            body: JSON.stringify({ note }),
        }),

    // Phase 2: Recurrence endpoints
    upcomingRecurring: () => request('/items/upcoming-recurring'),

    updateRecurrence: (id, data) =>
        request(`/items/${id}/recurrence`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),
};
