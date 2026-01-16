/**
 * Core API client logic
 */

// Use environment variable for production, fallback to /api for local dev with proxy
const API_BASE = import.meta.env.VITE_API_URL || '/api';
const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * Generic fetch wrapper with error handling and timeout
 */
export async function request(endpoint, options = {}) {
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

        // Return empty object for 204 No Content
        if (response.status === 204) {
            return {};
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
