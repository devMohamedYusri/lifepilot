/**
 * Voice API
 */
import { request } from './core';

const API_BASE = '/api'; // Needed for FormData fetch URLs not using request() wrapper strictly

export const voiceApi = {
    // Transcribe audio only
    transcribe: async (audioBlob, model = null, language = null) => {
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');
        if (model) formData.append('model', model);
        if (language) formData.append('language', language);

        const response = await fetch(`${API_BASE}/voice/transcribe`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Transcription failed');
        }

        return response.json();
    },

    // Transcribe and create item(s)
    capture: async (audioBlob, model = null, language = null) => {
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');
        if (model) formData.append('model', model);
        if (language) formData.append('language', language);

        const response = await fetch(`${API_BASE}/voice/capture`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Voice capture failed');
        }

        return response.json();
    },

    // Get available models
    getModels: () => request('/voice/models'),

    // Settings
    getSettings: () => request('/voice/settings'),
    updateSettings: (settings) =>
        request('/voice/settings', {
            method: 'PATCH',
            body: JSON.stringify(settings),
        }),

    // History
    getHistory: (limit = 20) => request(`/voice/history?limit=${limit}`),
};
