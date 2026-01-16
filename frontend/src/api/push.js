/**
 * Push Notifications API
 */
import { request } from './core';

export const pushApi = {
    // Status
    getStatus: () => request('/push/status'),

    // VAPID key for subscription
    getVapidKey: () => request('/push/vapid-key'),

    // Subscribe
    subscribe: (subscription, deviceName = null) =>
        request('/push/subscribe', {
            method: 'POST',
            body: JSON.stringify({
                endpoint: subscription.endpoint,
                keys: {
                    p256dh: subscription.toJSON().keys.p256dh,
                    auth: subscription.toJSON().keys.auth
                },
                device_name: deviceName
            }),
        }),

    // Unsubscribe
    unsubscribe: (endpoint) =>
        request(`/push/unsubscribe?endpoint=${encodeURIComponent(endpoint)}`, {
            method: 'DELETE',
        }),

    // Subscriptions list
    getSubscriptions: () => request('/push/subscriptions'),

    // Preferences
    getPreferences: () => request('/push/preferences'),
    updatePreferences: (prefs) =>
        request('/push/preferences', {
            method: 'PATCH',
            body: JSON.stringify(prefs),
        }),

    // Test
    sendTest: (title, body) =>
        request('/push/test', {
            method: 'POST',
            body: JSON.stringify({ title, body }),
        }),
};
