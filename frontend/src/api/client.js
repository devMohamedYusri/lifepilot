/**
 * API client for LifePilot backend
 */

const API_BASE = '/api';
const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * Generic fetch wrapper with error handling and timeout
 */
async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const timeout = options.timeout || DEFAULT_TIMEOUT;

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        signal: controller.signal,
        ...options,
    };

    try {
        const response = await fetch(url, config);
        clearTimeout(timeoutId);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.message || error.detail || `HTTP error ${response.status}`);
        }

        return response.json();
    } catch (error) {
        clearTimeout(timeoutId);

        if (error.name === 'AbortError') {
            throw new Error('Request timed out. Please try again.');
        }
        throw error;
    }
}

/**
 * Items API
 */
export const itemsApi = {
    create: (content) =>
        request('/items', {
            method: 'POST',
            body: JSON.stringify({ content }),
        }),

    list: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.type) params.set('type', filters.type);
        if (filters.status) params.set('status', filters.status);
        if (filters.include_snoozed) params.set('include_snoozed', 'true');
        const query = params.toString();
        return request(`/items${query ? `?${query}` : ''}`);
    },

    update: (id, data) =>
        request(`/items/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    delete: (id) =>
        request(`/items/${id}`, { method: 'DELETE' }),

    // Phase 2: Follow-up endpoints
    needsFollowup: () => request('/items/needs-followup'),

    followUp: (id, note = null) =>
        request(`/items/${id}/follow-up`, {
            method: 'POST',
            body: JSON.stringify({ note }),
        }),

    // Phase 2: Recurrence endpoints
    upcomingRecurring: () => request('/items/upcoming-recurring'),

    updateRecurrence: (id, data) =>
        request(`/items/${id}/recurrence`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),
};

/**
 * Focus API
 */
export const focusApi = {
    getToday: () => request('/focus/today'),
};

/**
 * Decisions API - Phase 2 (expanded)
 */
export const decisionsApi = {
    expand: (itemId, data = {}) =>
        request(`/decisions/${itemId}/expand`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    list: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.status) params.set('status', filters.status);
        if (filters.tag) params.set('tag', filters.tag);
        if (filters.item_id) params.set('item_id', filters.item_id);
        const query = params.toString();
        return request(`/decisions${query ? `?${query}` : ''}`);
    },

    get: (id) => request(`/decisions/${id}`),

    update: (id, data) =>
        request(`/decisions/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    recordOutcome: (id, outcome) =>
        request(`/decisions/${id}/record-outcome`, {
            method: 'POST',
            body: JSON.stringify(outcome),
        }),

    dueForReview: () => request('/decisions/due-for-review'),

    getInsights: (months = 6) => request(`/decisions/insights?months=${months}`),

    getStats: () => request('/decisions/stats'),
};

/**
 * Bookmarks API - Phase 2A
 */
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

/**
 * Health API
 */
export const healthApi = {
    check: () => request('/health'),
};

/**
 * Search API - Phase 2A
 */
export const searchApi = {
    search: (query, types = null) =>
        request('/search', {
            method: 'POST',
            body: JSON.stringify({ query, types }),
        }),

    suggestions: () => request('/search/suggestions'),
};

/**
 * Reviews API - Phase 2A Weekly Review
 */
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

/**
 * Contacts API - Phase 2B Personal CRM
 */
export const contactsApi = {
    create: (data) =>
        request('/contacts', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/contacts${query ? '?' + query : ''}`);
    },

    get: (id) => request(`/contacts/${id}`),

    update: (id, data) =>
        request(`/contacts/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    delete: (id) =>
        request(`/contacts/${id}`, {
            method: 'DELETE',
        }),

    logInteraction: (contactId, data) =>
        request(`/contacts/${contactId}/interactions`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    getInteractions: (contactId) => request(`/contacts/${contactId}/interactions`),

    needsAttention: () => request('/contacts/needs-attention'),

    suggestions: () => request('/contacts/suggestions'),

    upcomingDates: (days = 30) => request(`/contacts/upcoming-dates?days=${days}`),

    stats: () => request('/contacts/stats'),
};

/**
 * Energy API - Phase 2B Energy & Focus Logger
 */
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

/**
 * Notifications API - Phase 2B Smart Notifications
 */
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

/**
 * Patterns API (Phase 3)
 */
export const patternsApi = {
    analyze: (options = {}) =>
        request('/patterns/analyze', {
            method: 'POST',
            body: JSON.stringify(options),
            timeout: 60000,  // Pattern analysis can take longer
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

/**
 * Suggestions API (Phase 3B)
 */
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

/**
 * Calendar API (Phase 3C)
 */
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

/**
 * Auth API (OAuth management)
 */
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

/**
 * Voice API (Groq Whisper transcription)
 */
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

/**
 * Push Notifications API
 */
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
/**
 * Agent API - Phase 5: Autonomous Agent
 */
export const agentApi = {
    chat: (message, sessionId = null) => request('/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId })
    }),

    listConversations: (limit = 20) => request(`/agent/conversations?limit=${limit}`),

    getConversation: (sessionId) => request(`/agent/conversations/${sessionId}`),

    getPendingActions: () => request('/agent/pending-actions'),

    approveAction: (actionId) => request(`/agent/actions/${actionId}/approve`, {
        method: 'POST'
    }),

    rejectAction: (actionId, feedback = null) => request(`/agent/actions/${actionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback })
    }),

    getStatus: () => request('/agent/status'),

    getSettings: () => request('/agent/settings'),

    updateSettings: (settings) => request('/agent/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    })
};
