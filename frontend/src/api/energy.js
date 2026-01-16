/**
 * Energy API
 */
import { request } from './core';

export const energyApi = {
    log: (data) =>
        request('/energy/log', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    quickLog: (energy, focus = null) =>
        request('/energy/quick', {
            method: 'POST',
            body: JSON.stringify({ energy, focus }),
        }),

    getLogs: (days = 7, time_block = null) => {
        const params = new URLSearchParams({ days });
        if (time_block) params.append('time_block', time_block);
        return request(`/energy/logs?${params}`);
    },

    today: () => request('/energy/today'),

    patterns: () => request('/energy/patterns'),

    bestTime: (task_type = 'deep_work') => request(`/energy/best-time?task_type=${task_type}`),

    stats: () => request('/energy/stats'),
};
