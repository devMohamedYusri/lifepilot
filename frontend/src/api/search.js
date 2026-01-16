/**
 * Search API
 */
import { request } from './core';

export const searchApi = {
    search: (query, types = null) =>
        request('/search', {
            method: 'POST',
            body: JSON.stringify({ query, types }),
        }),

    suggestions: () => request('/search/suggestions'),
};
