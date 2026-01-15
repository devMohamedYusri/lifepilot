/**
 * SuggestionToast - Non-intrusive toast notification for suggestions
 */
import { useState, useEffect } from 'react';
import { suggestionsApi } from '../api/client';

const SUGGESTION_ICONS = {
    morning_planning: '🌅',
    end_of_day_review: '🌆',
    energy_check: '⚡',
    overdue_nudge: '⏰',
    contact_reminder: '👋',
    reading_suggestion: '📚',
    achievement: '🏆',
    task_timing: '✨'
};

const PRIORITY_COLORS = {
    high: 'border-red-500/50 bg-red-500/10',
    medium: 'border-primary-500/50 bg-primary-500/10',
    low: 'border-surface-400/30 bg-surface-700/50'
};

export default function SuggestionToast({ suggestion, onDismiss, onAct, autoHideDuration = 10000 }) {
    const [isVisible, setIsVisible] = useState(true);
    const [isExiting, setIsExiting] = useState(false);

    useEffect(() => {
        if (autoHideDuration > 0) {
            const timer = setTimeout(() => {
                handleDismiss('ignored');
            }, autoHideDuration);
            return () => clearTimeout(timer);
        }
    }, [autoHideDuration]);

    const handleDismiss = async (type = 'dismissed') => {
        setIsExiting(true);
        try {
            await suggestionsApi.respond(suggestion.id, type);
        } catch (err) {
            console.error('Failed to record response:', err);
        }
        setTimeout(() => {
            setIsVisible(false);
            onDismiss?.(suggestion.id);
        }, 300);
    };

    const handleAct = async () => {
        try {
            await suggestionsApi.respond(suggestion.id, 'acted');
        } catch (err) {
            console.error('Failed to record action:', err);
        }
        onAct?.(suggestion);
        setIsVisible(false);
        onDismiss?.(suggestion.id);
    };

    if (!isVisible) return null;

    const icon = SUGGESTION_ICONS[suggestion.template_type] || '💡';
    const priorityStyle = PRIORITY_COLORS[suggestion.priority] || PRIORITY_COLORS.medium;

    return (
        <div
            className={`
                fixed bottom-4 right-4 max-w-sm w-full
                glass rounded-xl border ${priorityStyle}
                shadow-lg shadow-black/20
                transform transition-all duration-300 ease-out
                ${isExiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100'}
            `}
            style={{ zIndex: 9999 }}
        >
            <div className="p-4">
                <div className="flex items-start gap-3">
                    <span className="text-2xl">{icon}</span>
                    <div className="flex-1">
                        <h4 className="font-medium text-white">{suggestion.title}</h4>
                        <p className="text-sm text-surface-200/80 mt-1">{suggestion.message}</p>
                    </div>
                    <button
                        onClick={() => handleDismiss('dismissed')}
                        className="text-surface-400 hover:text-white transition-colors"
                    >
                        ✕
                    </button>
                </div>

                <div className="flex items-center justify-end gap-2 mt-3">
                    <button
                        onClick={() => handleDismiss('dismissed')}
                        className="px-3 py-1.5 text-sm text-surface-300 hover:text-white transition-colors"
                    >
                        Dismiss
                    </button>
                    <button
                        onClick={handleAct}
                        className="px-4 py-1.5 text-sm bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
                    >
                        {suggestion.deep_link === '/energy' ? 'Log Energy' :
                            suggestion.deep_link === '/people' ? 'View Contacts' :
                                suggestion.deep_link === '/bookmarks' ? 'Read Now' : 'Take Action'}
                    </button>
                </div>
            </div>
        </div>
    );
}

/**
 * SuggestionToastContainer - Manages multiple toast notifications
 */
export function SuggestionToastContainer({ suggestions, onNavigate }) {
    const [activeSuggestions, setActiveSuggestions] = useState([]);

    useEffect(() => {
        // Show new suggestions that aren't already displayed
        const newSuggestions = suggestions.filter(
            s => !activeSuggestions.find(a => a.id === s.id)
        );
        if (newSuggestions.length > 0) {
            setActiveSuggestions(prev => [...prev, ...newSuggestions].slice(-3)); // Max 3
        }
    }, [suggestions]);

    const handleDismiss = (id) => {
        setActiveSuggestions(prev => prev.filter(s => s.id !== id));
    };

    const handleAct = (suggestion) => {
        if (suggestion.deep_link && onNavigate) {
            onNavigate(suggestion.deep_link.replace('/', ''));
        }
        handleDismiss(suggestion.id);
    };

    return (
        <div className="fixed bottom-4 right-4 flex flex-col gap-2" style={{ zIndex: 9998 }}>
            {activeSuggestions.map((suggestion, index) => (
                <div key={suggestion.id} style={{ transform: `translateY(${index * -10}px)` }}>
                    <SuggestionToast
                        suggestion={suggestion}
                        onDismiss={handleDismiss}
                        onAct={handleAct}
                        autoHideDuration={10000 + index * 2000}
                    />
                </div>
            ))}
        </div>
    );
}
