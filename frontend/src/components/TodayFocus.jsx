import { useState, useEffect } from 'react';
import { focusApi } from '../api/client';
import { useMobile } from '../hooks/useMobile';

/**
 * Today's Focus section showing AI-selected priority items
 */
export default function TodayFocus({ items, onItemUpdate }) {
    const [focusData, setFocusData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const { isMobile } = useMobile();

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
            <div className={`glass rounded-2xl text-center ${isMobile ? 'p-4' : 'p-6'}`}>
                <div className={isMobile ? 'text-3xl mb-2' : 'text-4xl mb-3'}>🎯</div>
                <h2 className={`font-semibold text-white ${isMobile ? 'text-lg mb-1' : 'text-xl mb-2'}`}>Today's Focus</h2>
                <p className={`text-surface-200 ${isMobile ? 'text-sm' : 'text-base'}`}>
                    Capture some tasks in the inbox above to see your AI-powered daily focus.
                </p>
            </div>
        );
    }

    return (
        <div className="glass rounded-2xl overflow-hidden">
            {/* Header */}
            <div className={`border-b border-white/10 flex items-center justify-between
                    bg-gradient-to-r from-primary-600/20 to-purple-600/20
                    ${isMobile ? 'px-4 py-3' : 'px-6 py-4'}`}>
                <div className="flex items-center gap-3">
                    <span className={isMobile ? 'text-xl' : 'text-2xl'}>🎯</span>
                    <div>
                        <h2 className={`font-semibold text-white ${isMobile ? 'text-base' : 'text-xl'}`}>Today's Focus</h2>
                        <p className={`text-surface-200/80 ${isMobile ? 'text-xs' : 'text-sm'}`}>AI-selected priorities for maximum impact</p>
                    </div>
                </div>
                <button
                    onClick={fetchFocus}
                    disabled={loading}
                    className={`btn-ghost flex items-center gap-2 ${isMobile ? 'text-xs px-2 py-1' : 'text-sm'}`}
                >
                    {loading ? (
                        <>
                            <div className="spinner"></div>
                            {!isMobile && <span>Analyzing...</span>}
                        </>
                    ) : (
                        <>
                            <span>🔄</span>
                            {!isMobile && <span>Refresh Focus</span>}
                        </>
                    )}
                </button>
            </div>

            {/* Content */}
            <div className={isMobile ? 'p-4' : 'p-6'}>
                {error && (
                    <div className={`mb-4 px-4 py-2 bg-red-500/10 border border-red-500/30 
                        rounded-lg text-red-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>
                        ⚠️ {error}
                    </div>
                )}

                {loading && !focusData ? (
                    <div className={isMobile ? 'flex items-center justify-center py-6' : 'flex items-center justify-center py-8'}>
                        <div className="flex items-center gap-3 text-primary-400">
                            <div className="spinner"></div>
                            {!isMobile && <span>AI is analyzing your tasks...</span>}
                        </div>
                    </div>
                ) : focusData?.focus_items?.length > 0 ? (
                    <>
                        {/* Encouragement */}
                        {focusData.encouragement && (
                            <div className={`mb-4 bg-gradient-to-r from-emerald-500/10 to-primary-500/10 
                            border border-emerald-500/20 rounded-xl ${isMobile ? 'px-3 py-2' : 'px-4 py-3'}`}>
                                <p className={`text-emerald-300 italic ${isMobile ? 'text-xs' : 'text-sm'}`}>
                                    ✨ {focusData.encouragement}
                                </p>
                            </div>
                        )}

                        {/* Focus items */}
                        <div className={isMobile ? 'space-y-2' : 'space-y-3'}>
                            {focusData.focus_items.map((focusItem, index) => {
                                const itemDetails = getFocusItemDetails(focusItem);
                                if (!itemDetails) return null;

                                return (
                                    <div
                                        key={focusItem.id}
                                        className={`flex items-start rounded-xl bg-surface-800/50 
                             border border-surface-700 hover:border-primary-500/30 
                             transition-all duration-200 group
                             ${isMobile ? 'gap-2 p-3' : 'gap-4 p-4'}`}
                                    >
                                        {/* Priority number */}
                                        <div className={`rounded-full bg-gradient-to-br from-primary-500 to-purple-500 
                                  flex items-center justify-center text-white font-bold shrink-0
                                  ${isMobile ? 'w-6 h-6 text-xs' : 'w-8 h-8 text-sm'}`}>
                                            {index + 1}
                                        </div>

                                        {/* Content */}
                                        <div className="flex-1 min-w-0">
                                            <h3 className={`text-white font-medium ${isMobile ? 'text-sm' : 'text-base'}`}>
                                                {itemDetails.ai_summary || itemDetails.raw_content}
                                            </h3>
                                            <p className={`mt-1 text-primary-400/80 ${isMobile ? 'text-xs' : 'text-sm'}`}>
                                                💡 {focusItem.reason}
                                            </p>
                                            {itemDetails.ai_next_action && (
                                                <p className={`mt-1 text-surface-200/70 ${isMobile ? 'text-xs' : 'text-sm'}`}>
                                                    → {itemDetails.ai_next_action}
                                                </p>
                                            )}
                                        </div>

                                        {/* Due date if any */}
                                        {itemDetails.due_date && !isMobile && (
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
                    <div className={isMobile ? 'text-center py-4' : 'text-center py-6'}>
                        <p className={`text-surface-200 ${isMobile ? 'text-sm' : 'text-base'}`}>
                            Click {isMobile ? '"🔄"' : '"Refresh Focus"'} to get AI recommendations for today.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
