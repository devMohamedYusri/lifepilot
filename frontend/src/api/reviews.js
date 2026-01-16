/**
 * Reviews API
 */
import { request } from './core';

export const reviewsApi = {
    generate: (offsetWeeks = 0) =>
        request(`/reviews/generate?offset_weeks=${offsetWeeks}`, {
            method: 'POST',
        }),

    list: (limit = 10) => request(`/reviews?limit=${limit}`),

    current: () => request('/reviews/current'),

    saveReflection: (id, data) =>
        request(`/reviews/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),
};
