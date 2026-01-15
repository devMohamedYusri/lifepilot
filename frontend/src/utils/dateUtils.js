/**
 * Date formatting utilities for LifePilot
 */

/**
 * Format a date string for display
 * @param {string} dateStr - ISO date string
 * @param {object} options - Formatting options
 * @returns {string} Formatted date string
 */
export function formatDate(dateStr, options = {}) {
    if (!dateStr) return '';

    try {
        const date = new Date(dateStr);
        const {
            includeTime = false,
            relative = false,
            short = false
        } = options;

        if (relative) {
            return formatRelativeDate(date);
        }

        if (short) {
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric'
            });
        }

        const dateOptions = {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        };

        if (includeTime) {
            Object.assign(dateOptions, {
                hour: 'numeric',
                minute: '2-digit'
            });
        }

        return date.toLocaleDateString('en-US', dateOptions);
    } catch {
        return dateStr;
    }
}

/**
 * Format a date relative to now (e.g., "2 days ago", "in 3 hours")
 * @param {Date} date - Date object to format
 * @returns {string} Relative date string
 */
export function formatRelativeDate(date) {
    const now = new Date();
    const diffMs = date - now;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffDays === 0) {
        if (diffHours === 0) {
            if (diffMinutes === 0) return 'just now';
            return diffMinutes > 0
                ? `in ${diffMinutes} minutes`
                : `${Math.abs(diffMinutes)} minutes ago`;
        }
        return diffHours > 0
            ? `in ${diffHours} hours`
            : `${Math.abs(diffHours)} hours ago`;
    }

    if (diffDays === 1) return 'tomorrow';
    if (diffDays === -1) return 'yesterday';

    return diffDays > 0
        ? `in ${diffDays} days`
        : `${Math.abs(diffDays)} days ago`;
}

/**
 * Check if a date is today
 * @param {string} dateStr - ISO date string
 * @returns {boolean}
 */
export function isToday(dateStr) {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    const today = new Date();
    return date.toDateString() === today.toDateString();
}

/**
 * Check if a date is in the past
 * @param {string} dateStr - ISO date string
 * @returns {boolean}
 */
export function isPast(dateStr) {
    if (!dateStr) return false;
    return new Date(dateStr) < new Date();
}

/**
 * Check if a date is within the next N days
 * @param {string} dateStr - ISO date string
 * @param {number} days - Number of days
 * @returns {boolean}
 */
export function isWithinDays(dateStr, days) {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    const now = new Date();
    const future = new Date();
    future.setDate(future.getDate() + days);
    return date >= now && date <= future;
}

/**
 * Get start of current week (Monday)
 * @returns {Date}
 */
export function getWeekStart() {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(now.setDate(diff));
}

/**
 * Format duration in minutes to readable string
 * @param {number} minutes - Duration in minutes
 * @returns {string} Formatted duration
 */
export function formatDuration(minutes) {
    if (!minutes) return '';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}
