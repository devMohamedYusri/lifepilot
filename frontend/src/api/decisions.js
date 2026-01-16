/**
 * Decisions API
 */
import { request } from './core';

export const decisionsApi = {
    expand: (itemId, data = {}) =>
        request(`/decisions/${itemId}/expand`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    list: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.status) params.set('status', filters.status);
        if (filters.tag) params.set('tag', filters.tag);
        if (filters.item_id) params.set('item_id', filters.item_id);
        const query = params.toString();
        return request(`/decisions${query ? `?${query}` : ''}`);
    },

    get: (id) => request(`/decisions/${id}`),

    update: (id, data) =>
        request(`/decisions/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    recordOutcome: (id, outcome) =>
        request(`/decisions/${id}/record-outcome`, {
            method: 'POST',
            body: JSON.stringify(outcome),
        }),

    dueForReview: () => request('/decisions/due-for-review'),

    getInsights: (months = 6) => request(`/decisions/insights?months=${months}`),

    getStats: () => request('/decisions/stats'),
};
