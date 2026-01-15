import { useState, useEffect } from 'react';
import { reviewsApi } from '../api/client';

/**
 * Weekly Review component
 */
export default function WeeklyReview() {
    const [review, setReview] = useState(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [saving, setSaving] = useState(false);
    const [pastReviews, setPastReviews] = useState([]);
    const [reflection, setReflection] = useState({
        wins: '',
        challenges: '',
        next_week_focus: '',
    });

    useEffect(() => {
        fetchCurrentReview();
        fetchPastReviews();
    }, []);

    const fetchCurrentReview = async () => {
        try {
            const data = await reviewsApi.current();
            if (data.exists !== false) {
                setReview(data);
                setReflection({
                    wins: data.wins || '',
                    challenges: data.challenges || '',
                    next_week_focus: data.next_week_focus || '',
                });
            }
        } catch (err) {
            console.error('Failed to fetch current review:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchPastReviews = async () => {
        try {
            const data = await reviewsApi.list(5);
            setPastReviews(data);
        } catch (err) {
            console.error('Failed to fetch past reviews:', err);
        }
    };

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            const data = await reviewsApi.generate(0);
            setReview(data);
            setReflection({
                wins: '',
                challenges: '',
                next_week_focus: '',
            });
        } catch (err) {
            console.error('Failed to generate review:', err);
        } finally {
            setGenerating(false);
        }
    };

    const handleSaveReflection = async () => {
        if (!review?.id) return;
        setSaving(true);
        try {
            await reviewsApi.saveReflection(review.id, reflection);
        } catch (err) {
            console.error('Failed to save reflection:', err);
        } finally {
            setSaving(false);
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric'
        });
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="flex items-center gap-3 text-primary-400">
                    <div className="spinner"></div>
                    <span>Loading review...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white">📊 Weekly Review</h2>
                    <p className="text-surface-300">Reflect on your week and plan ahead</p>
                </div>
                <button
                    onClick={handleGenerate}
                    disabled={generating}
                    className="btn-primary"
                >
                    {generating ? '🔄 Generating...' : '✨ Generate This Week'}
                </button>
            </div>

            {review ? (
                <>
                    {/* Week Date Range */}
                    <div className="glass rounded-lg px-4 py-2 inline-block">
                        <span className="text-surface-300">Week of </span>
                        <span className="text-white font-medium">
                            {formatDate(review.week_start)} - {formatDate(review.week_end)}
                        </span>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="glass rounded-xl p-4 text-center">
                            <div className="text-3xl font-bold text-emerald-400">{review.items_completed || 0}</div>
                            <div className="text-surface-300 text-sm">Tasks Completed</div>
                        </div>
                        <div className="glass rounded-xl p-4 text-center">
                            <div className="text-3xl font-bold text-blue-400">{review.bookmarks_read || 0}</div>
                            <div className="text-surface-300 text-sm">Bookmarks Read</div>
                        </div>
                        <div className="glass rounded-xl p-4 text-center">
                            <div className="text-3xl font-bold text-amber-400">{review.decisions_made || 0}</div>
                            <div className="text-surface-300 text-sm">Decisions Made</div>
                        </div>
                        <div className="glass rounded-xl p-4 text-center">
                            <div className="text-3xl font-bold text-purple-400">{review.follow_ups || 0}</div>
                            <div className="text-surface-300 text-sm">Follow-ups Sent</div>
                        </div>
                    </div>

                    {/* AI Summary */}
                    <div className="glass rounded-xl p-6 space-y-4">
                        <h3 className="text-lg font-semibold text-white">🎯 Accomplishments</h3>
                        {review.accomplishments?.length > 0 ? (
                            <ul className="space-y-2">
                                {review.accomplishments.map((item, i) => (
                                    <li key={i} className="flex items-start gap-2 text-surface-200">
                                        <span className="text-emerald-400">✓</span>
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="text-surface-400">No accomplishments recorded yet.</p>
                        )}
                    </div>

                    {/* Themes & Insights */}
                    {(review.themes?.length > 0 || review.insights) && (
                        <div className="glass rounded-xl p-6 space-y-4">
                            <h3 className="text-lg font-semibold text-white">💡 Themes & Insights</h3>
                            {review.themes?.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {review.themes.map((theme, i) => (
                                        <span key={i} className="badge bg-primary-500/20 text-primary-400 border-primary-500/30">
                                            {theme}
                                        </span>
                                    ))}
                                </div>
                            )}
                            {review.insights && (
                                <p className="text-surface-200">{review.insights}</p>
                            )}
                        </div>
                    )}

                    {/* Encouragement */}
                    {review.encouragement && (
                        <div className="glass rounded-xl p-6 bg-emerald-500/10 border border-emerald-500/20">
                            <p className="text-emerald-400 text-lg">{review.encouragement}</p>
                        </div>
                    )}

                    {/* Reflection Prompts & Form */}
                    <div className="glass rounded-xl p-6 space-y-4">
                        <h3 className="text-lg font-semibold text-white">📝 Your Reflection</h3>

                        {review.reflection_prompts?.length > 0 && (
                            <div className="space-y-2 mb-4">
                                <p className="text-surface-400 text-sm">Consider these questions:</p>
                                {review.reflection_prompts.map((prompt, i) => (
                                    <p key={i} className="text-primary-400/80 text-sm italic">• {prompt}</p>
                                ))}
                            </div>
                        )}

                        <div className="space-y-4">
                            <div>
                                <label className="text-surface-300 text-sm font-medium block mb-2">🏆 Wins this week</label>
                                <textarea
                                    value={reflection.wins}
                                    onChange={(e) => setReflection(prev => ({ ...prev, wins: e.target.value }))}
                                    placeholder="What went well?"
                                    className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white text-sm"
                                    rows={2}
                                />
                            </div>
                            <div>
                                <label className="text-surface-300 text-sm font-medium block mb-2">🚧 Challenges faced</label>
                                <textarea
                                    value={reflection.challenges}
                                    onChange={(e) => setReflection(prev => ({ ...prev, challenges: e.target.value }))}
                                    placeholder="What was difficult?"
                                    className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white text-sm"
                                    rows={2}
                                />
                            </div>
                            <div>
                                <label className="text-surface-300 text-sm font-medium block mb-2">🎯 Focus for next week</label>
                                <textarea
                                    value={reflection.next_week_focus}
                                    onChange={(e) => setReflection(prev => ({ ...prev, next_week_focus: e.target.value }))}
                                    placeholder="What's your main priority?"
                                    className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white text-sm"
                                    rows={2}
                                />
                            </div>
                            <button
                                onClick={handleSaveReflection}
                                disabled={saving}
                                className="btn-primary"
                            >
                                {saving ? 'Saving...' : '💾 Save Reflection'}
                            </button>
                        </div>
                    </div>
                </>
            ) : (
                /* Empty State */
                <div className="glass rounded-xl p-12 text-center">
                    <div className="text-5xl mb-4">📊</div>
                    <h3 className="text-xl font-semibold text-white mb-2">No Review Yet</h3>
                    <p className="text-surface-300 mb-6">Generate your weekly review to see stats and insights.</p>
                    <button
                        onClick={handleGenerate}
                        disabled={generating}
                        className="btn-primary"
                    >
                        {generating ? '🔄 Generating...' : '✨ Generate This Week\'s Review'}
                    </button>
                </div>
            )}

            {/* Past Reviews */}
            {pastReviews.length > 0 && (
                <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-white">📚 Past Reviews</h3>
                    <div className="space-y-2">
                        {pastReviews.map(r => (
                            <div key={r.id} className="glass rounded-lg p-4 flex items-center justify-between">
                                <div>
                                    <span className="text-white font-medium">
                                        {formatDate(r.week_start)} - {formatDate(r.week_end)}
                                    </span>
                                    <div className="text-surface-400 text-sm">
                                        {r.items_completed} tasks • {r.decisions_made} decisions
                                    </div>
                                </div>
                                {r.next_week_focus && (
                                    <span className="text-primary-400 text-sm">Focus: {r.next_week_focus}</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
