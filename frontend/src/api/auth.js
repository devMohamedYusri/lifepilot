/**
 * Auth API
 */
import { request } from './core';

export const authApi = {
    // Status
    getStatus: () => request('/auth/status'),
    getSetupInstructions: () => request('/auth/setup-instructions'),

    // Credentials
    saveCredentials: (clientId, clientSecret, redirectUri = null) =>
        request('/auth/credentials', {
            method: 'POST',
            body: JSON.stringify({
                client_id: clientId,
                client_secret: clientSecret,
                redirect_uri: redirectUri
            }),
        }),
    testCredentials: (clientId, clientSecret) =>
        request('/auth/test', {
            method: 'POST',
            body: JSON.stringify({
                client_id: clientId,
                client_secret: clientSecret
            }),
        }),

    // OAuth flow
    initiateGoogle: (redirectAfter = null) => {
        let url = '/auth/google';
        if (redirectAfter) url += `?redirect_after=${encodeURIComponent(redirectAfter)}`;
        return request(url);
    },

    // Connections
    getConnections: () => request('/auth/connections'),
    deleteConnection: (connectionId) =>
        request(`/auth/connections/${connectionId}`, { method: 'DELETE' }),
    refreshConnection: (connectionId) =>
        request(`/auth/connections/${connectionId}/refresh`, { method: 'POST' }),
};
