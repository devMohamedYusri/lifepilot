/**
 * Helper APIs: Health, Focus, Patterns, Suggestions
 */
import { request } from './core';

export const healthApi = {
    check: () => request('/health'),
};

export const focusApi = {
    getToday: () => request('/focus/today'),
};

export const patternsApi = {
    analyze: (options = {}) =>
        request('/patterns/analyze', {
            method: 'POST',
            body: JSON.stringify(options),
            timeout: 60000,
        }),

    list: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.pattern_type) params.set('pattern_type', filters.pattern_type);
        if (filters.category) params.set('category', filters.category);
        if (filters.min_confidence) params.set('min_confidence', filters.min_confidence);
        if (filters.active_only !== undefined) params.set('active_only', filters.active_only);
        const query = params.toString();
        return request(`/patterns${query ? `?${query}` : ''}`);
    },

    get: (id) => request(`/patterns/${id}`),

    getInsights: () => request('/patterns/insights'),

    getDashboard: () => request('/patterns/dashboard'),

    submitFeedback: (patternId, feedback) =>
        request(`/patterns/${patternId}/feedback`, {
            method: 'POST',
            body: JSON.stringify(feedback),
        }),

    dismissInsight: (insightId) =>
        request(`/patterns/insights/${insightId}/dismiss`, {
            method: 'POST',
        }),

    actOnInsight: (insightId) =>
        request(`/patterns/insights/${insightId}/act`, {
            method: 'POST',
        }),
};

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
