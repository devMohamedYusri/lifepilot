/**
 * Notifications API
 */
import { request } from './core';

export const notificationsApi = {
    pending: () => request('/notifications/pending'),

    count: () => request('/notifications/count'),

    dismiss: (id) =>
        request(`/notifications/${id}/dismiss`, {
            method: 'POST',
        }),

    act: (id) =>
        request(`/notifications/${id}/act`, {
            method: 'POST',
        }),

    generate: () => request('/notifications/generate'),

    digest: () => request('/notifications/digest'),

    getSettings: () => request('/notifications/settings'),

    updateSettings: (type, data) =>
        request(`/notifications/settings/${type}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    clearAll: () =>
        request('/notifications/clear-all', {
            method: 'POST',
        }),
};
