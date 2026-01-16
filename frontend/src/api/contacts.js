/**
 * Contacts API
 */
import { request } from './core';

export const contactsApi = {
    create: (data) =>
        request('/contacts', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/contacts${query ? '?' + query : ''}`);
    },

    get: (id) => request(`/contacts/${id}`),

    update: (id, data) =>
        request(`/contacts/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    delete: (id) =>
        request(`/contacts/${id}`, {
            method: 'DELETE',
        }),

    logInteraction: (contactId, data) =>
        request(`/contacts/${contactId}/interactions`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    getInteractions: (contactId) => request(`/contacts/${contactId}/interactions`),

    needsAttention: () => request('/contacts/needs-attention'),

    suggestions: () => request('/contacts/suggestions'),

    upcomingDates: (days = 30) => request(`/contacts/upcoming-dates?days=${days}`),

    stats: () => request('/contacts/stats'),
};
