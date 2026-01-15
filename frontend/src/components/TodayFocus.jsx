import { useState, useEffect } from 'react';
import { focusApi } from '../api/client';

/**
 * Today's Focus section showing AI-selected priority items
 */
export default function TodayFocus({ items, onItemUpdate }) {
    const [focusData, setFocusData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchFocus = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await focusApi.getToday();
            setFocusData(data);
        } catch (err) {
            setError(err.message || 'Failed to get focus items');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (items.length > 0) {
            fetchFocus();
        }
    }, []);

    const getFocusItemDetails = (focusItem) => {
        return items.find(i => i.id === focusItem.id);
    };

    if (items.length === 0) {
        return (
            <div className="glass rounded-2xl p-6 text-center">
                <div className="text-4xl mb-3">🎯</div>
                <h2 className="text-xl font-semibold text-white mb-2">Today's Focus</h2>
                <p className="text-surface-200">
                    Capture some tasks in the inbox above to see your AI-powered daily focus.
                </p>
            </div>
        );
    }

    return (
        <div className="glass rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between
                    bg-gradient-to-r from-primary-600/20 to-purple-600/20">
                <div className="flex items-center gap-3">
                    <span className="text-2xl">🎯</span>
                    <div>
                        <h2 className="text-xl font-semibold text-white">Today's Focus</h2>
                        <p className="text-sm text-surface-200/80">AI-selected priorities for maximum impact</p>
                    </div>
                </div>
                <button
                    onClick={fetchFocus}
                    disabled={loading}
                    className="btn-ghost flex items-center gap-2 text-sm"
                >
                    {loading ? (
                        <>
                            <div className="spinner"></div>
                            <span>Analyzing...</span>
                        </>
                    ) : (
                        <>
                            <span>🔄</span>
                            <span>Refresh Focus</span>
                        </>
                    )}
                </button>
            </div>

            {/* Content */}
            <div className="p-6">
                {error && (
                    <div className="mb-4 px-4 py-2 bg-red-500/10 border border-red-500/30 
                        rounded-lg text-red-400 text-sm">
                        ⚠️ {error}
                    </div>
                )}

                {loading && !focusData ? (
                    <div className="flex items-center justify-center py-8">
                        <div className="flex items-center gap-3 text-primary-400">
                            <div className="spinner"></div>
                            <span>AI is analyzing your tasks...</span>
                        </div>
                    </div>
                ) : focusData?.focus_items?.length > 0 ? (
                    <>
                        {/* Encouragement */}
                        {focusData.encouragement && (
                            <div className="mb-4 px-4 py-3 bg-gradient-to-r from-emerald-500/10 to-primary-500/10 
                            border border-emerald-500/20 rounded-xl">
                                <p className="text-emerald-300 text-sm italic">
                                    ✨ {focusData.encouragement}
                                </p>
                            </div>
                        )}

                        {/* Focus items */}
                        <div className="space-y-3">
                            {focusData.focus_items.map((focusItem, index) => {
                                const itemDetails = getFocusItemDetails(focusItem);
                                if (!itemDetails) return null;

                                return (
                                    <div
                                        key={focusItem.id}
                                        className="flex items-start gap-4 p-4 rounded-xl bg-surface-800/50 
                             border border-surface-700 hover:border-primary-500/30 
                             transition-all duration-200 group"
                                    >
                                        {/* Priority number */}
                                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-500 
                                  flex items-center justify-center text-white font-bold shrink-0">
                                            {index + 1}
                                        </div>

                                        {/* Content */}
                                        <div className="flex-1 min-w-0">
                                            <h3 className="text-white font-medium">
                                                {itemDetails.ai_summary || itemDetails.raw_content}
                                            </h3>
                                            <p className="mt-1 text-sm text-primary-400/80">
                                                💡 {focusItem.reason}
                                            </p>
                                            {itemDetails.ai_next_action && (
                                                <p className="mt-1 text-sm text-surface-200/70">
                                                    → {itemDetails.ai_next_action}
                                                </p>
                                            )}
                                        </div>

                                        {/* Due date if any */}
                                        {itemDetails.due_date && (
                                            <span className="badge bg-surface-700/50 text-surface-200 border border-surface-600 shrink-0">
                                                📅 {new Date(itemDetails.due_date).toLocaleDateString('en-US', {
                                                    month: 'short',
                                                    day: 'numeric'
                                                })}
                                            </span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </>
                ) : (
                    <div className="text-center py-6">
                        <p className="text-surface-200">
                            Click "Refresh Focus" to get AI recommendations for today.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
