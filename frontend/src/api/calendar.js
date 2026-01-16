/**
 * Calendar API
 */
import { request } from './core';

export const calendarApi = {
    // OAuth
    getAuthUrl: (provider) => request(`/calendar/auth/${provider}`),

    // Connections
    getConnections: () => request('/calendar/connections'),
    deleteConnection: (id) => request(`/calendar/connections/${id}`, { method: 'DELETE' }),

    // Sync
    triggerSync: (connectionId, direction = 'bidirectional') =>
        request(`/calendar/sync/${connectionId}?direction=${direction}`, { method: 'POST' }),
    getSyncLogs: (connectionId, limit = 10) =>
        request(`/calendar/sync/${connectionId}/logs?limit=${limit}`),

    // Events
    getEvents: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/calendar/events${query ? `?${query}` : ''}`);
    },

    // Free Time
    getFreeBlocks: (date, minDuration = null) => {
        let url = `/calendar/free-blocks?date=${date}`;
        if (minDuration) url += `&min_duration=${minDuration}`;
        return request(url);
    },
    getFocusSuggestion: (date, duration = 90) =>
        request(`/calendar/focus-suggestion?date=${date}&duration=${duration}`),
    checkAvailability: (startTime, endTime) =>
        request(`/calendar/availability?start_time=${startTime}&end_time=${endTime}`),
    getDaySummary: (date) => request(`/calendar/day-summary?date=${date}`),

    // Preferences
    getPreferences: () => request('/calendar/preferences'),
    updatePreferences: (preferences) =>
        request('/calendar/preferences', {
            method: 'PATCH',
            body: JSON.stringify(preferences),
        }),
};
