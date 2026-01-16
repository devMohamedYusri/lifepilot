/**
 * Bookmarks API
 */
import { request } from './core';

export const bookmarksApi = {
    create: (url, source = null, notes = null) =>
        request('/bookmarks', {
            method: 'POST',
            body: JSON.stringify({ url, source, notes }),
        }),

    list: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.status) params.set('status', filters.status);
        if (filters.category) params.set('category', filters.category);
        if (filters.complexity) params.set('complexity', filters.complexity);
        if (filters.priority) params.set('priority', filters.priority);
        if (filters.tag) params.set('tag', filters.tag);
        if (filters.search) params.set('search', filters.search);
        if (filters.sort) params.set('sort', filters.sort);
        const query = params.toString();
        return request(`/bookmarks${query ? `?${query}` : ''}`);
    },

    get: (id) => request(`/bookmarks/${id}`),

    update: (id, data) =>
        request(`/bookmarks/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    delete: (id) =>
        request(`/bookmarks/${id}`, { method: 'DELETE' }),

    startSession: (id) =>
        request(`/bookmarks/${id}/start-session`, { method: 'POST' }),

    complete: (id) =>
        request(`/bookmarks/${id}/complete`, { method: 'POST' }),

    getReadingQueue: (minutes = 30, energy = 'medium') =>
        request(`/bookmarks/reading-queue?minutes=${minutes}&energy=${energy}`),

    getStats: () => request('/bookmarks/stats'),
};
