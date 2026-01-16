/**
 * Suggestions API
 */
import { request } from './core';

export const suggestionsApi = {
    list: (limit = 5) =>
        request(`/suggestions?limit=${limit}`),

    generate: (force = false) =>
        request(`/suggestions/generate?force=${force}`, {
            method: 'POST',
        }),

    respond: (suggestionId, responseType) =>
        request(`/suggestions/${suggestionId}/response`, {
            method: 'POST',
            body: JSON.stringify({ response_type: responseType }),
        }),

    getPreferences: () => request('/suggestions/preferences'),

    updatePreferences: (preferences) =>
        request('/suggestions/preferences', {
            method: 'PATCH',
            body: JSON.stringify(preferences),
        }),

    getStats: () => request('/suggestions/stats'),
};
