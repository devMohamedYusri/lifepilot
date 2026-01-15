/**
 * Text and number formatting utilities
 */

/**
 * Truncate text to a maximum length with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export function truncate(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

/**
 * Capitalize first letter of a string
 * @param {string} text - Text to capitalize
 * @returns {string} Capitalized text
 */
export function capitalize(text) {
    if (!text) return '';
    return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Convert snake_case or kebab-case to Title Case
 * @param {string} text - Text to convert
 * @returns {string} Title case text
 */
export function toTitleCase(text) {
    if (!text) return '';
    return text
        .replace(/[-_]/g, ' ')
        .replace(/\b\w/g, char => char.toUpperCase());
}

/**
 * Format a number with commas
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
export function formatNumber(num) {
    if (num === null || num === undefined) return '';
    return num.toLocaleString();
}

/**
 * Format a percentage
 * @param {number} value - Value (0-100 or 0-1)
 * @param {boolean} isDecimal - Whether value is 0-1 (default: false)
 * @returns {string} Formatted percentage
 */
export function formatPercent(value, isDecimal = false) {
    if (value === null || value === undefined) return '';
    const percent = isDecimal ? value * 100 : value;
    return `${Math.round(percent)}%`;
}

/**
 * Sanitize text to prevent XSS (basic HTML escape)
 * @param {string} text - Text to sanitize
 * @returns {string} Sanitized text
 */
export function sanitizeText(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Extract domain from URL
 * @param {string} url - Full URL
 * @returns {string} Domain name
 */
export function extractDomain(url) {
    if (!url) return '';
    try {
        const parsed = new URL(url);
        return parsed.hostname.replace('www.', '');
    } catch {
        return url;
    }
}

/**
 * Parse JSON tags from string
 * @param {string} tagsStr - JSON string or comma-separated tags
 * @returns {string[]} Array of tags
 */
export function parseTags(tagsStr) {
    if (!tagsStr) return [];
    try {
        const parsed = JSON.parse(tagsStr);
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        // Fall back to comma-separated
        return tagsStr.split(',').map(t => t.trim()).filter(Boolean);
    }
}
