import { useState, useEffect } from 'react';
import { decisionsApi } from '../api/client';

/**
 * Status config for decisions
 */
const STATUS_CONFIG = {
    deliberating: { label: 'Deliberating', icon: '🤔', color: 'bg-yellow-500/20 text-yellow-400' },
    decided: { label: 'Decided', icon: '✅', color: 'bg-blue-500/20 text-blue-400' },
    awaiting_outcome: { label: 'Awaiting Outcome', icon: '⏳', color: 'bg-orange-500/20 text-orange-400' },
    completed: { label: 'Completed', icon: '📊', color: 'bg-emerald-500/20 text-emerald-400' },
};

/**
 * Decision Card component
 */
function DecisionCard({ decision, onUpdate, onRecordOutcome }) {
    const [showOutcome, setShowOutcome] = useState(false);
    const [outcomeData, setOutcomeData] = useState({
        actual_outcome: '',
        outcome_rating: 3,
        expectation_matched: 3,
        lessons: '',
        would_change: '',
    });
    const [loading, setLoading] = useState(false);

    const status = STATUS_CONFIG[decision.status] || STATUS_CONFIG.deliberating;

    // Parse options
    let options = [];
    try {
        options = JSON.parse(decision.options || '[]');
    } catch (e) { }

    // Parse tags
    let tags = [];
    try {
        tags = JSON.parse(decision.tags || '[]');
    } catch (e) { }

    const handleRecordOutcome = async () => {
        setLoading(true);
        try {
            const updated = await decisionsApi.recordOutcome(decision.id, outcomeData);
            if (onRecordOutcome) onRecordOutcome(decision.id, updated);
            setShowOutcome(false);
        } catch (err) {
            console.error('Failed to record outcome:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card item-enter">
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                        <span className={`badge ${status.color}`}>
                            {status.icon} {status.label}
                        </span>
                        {decision.confidence && (
                            <span className="badge bg-purple-500/20 text-purple-400">
                                {decision.confidence}/5 confidence
                            </span>
                        )}
                        {decision.rating && (
                            <span className="badge bg-emerald-500/20 text-emerald-400">
                                ⭐ {decision.rating}/5
                            </span>
                        )}
                    </div>

                    <h3 className="text-white font-medium">
                        {decision.context || decision.situation || 'Untitled Decision'}
                    </h3>

                    {/* Tags */}
                    {tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                            {tags.map((tag, i) => (
                                <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-surface-700/50 text-surface-300">
                                    {tag}
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                <span className="text-xs text-surface-400">
                    {new Date(decision.created_at).toLocaleDateString()}
                </span>
            </div>

            {/* Options (if deliberating or decided) */}
            {options.length > 0 && (decision.status === 'deliberating' || decision.status === 'decided') && (
                <div className="mt-4 space-y-2">
                    <p className="text-sm text-surface-300 font-medium">Options:</p>
                    {options.map((opt, i) => (
                        <div key={i} className={`p-2 rounded-lg ${decision.chosen_option === opt.option ? 'bg-primary-500/20 border border-primary-500/30' : 'bg-surface-800/50'}`}>
                            <p className="text-white text-sm">
                                {decision.chosen_option === opt.option && '✓ '}
                                {opt.option}
                            </p>
                        </div>
                    ))}
                </div>
            )}

            {/* Chosen + Reasoning (if decided) */}
            {decision.chosen_option && decision.reasoning && (
                <div className="mt-4 p-3 bg-surface-800/50 rounded-lg">
                    <p className="text-surface-300 text-sm"><strong>Reasoning:</strong> {decision.reasoning}</p>
                    {decision.expected_outcome && (
                        <p className="text-surface-300 text-sm mt-2"><strong>Expected:</strong> {decision.expected_outcome}</p>
                    )}
                </div>
            )}

            {/* Outcome (if completed) */}
            {decision.actual_outcome && (
                <div className="mt-4 p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                    <p className="text-emerald-400 text-sm"><strong>Outcome:</strong> {decision.actual_outcome}</p>
                    {decision.lessons && (
                        <p className="text-surface-300 text-sm mt-2"><strong>Lessons:</strong> {decision.lessons}</p>
                    )}
                </div>
            )}

            {/* Actions */}
            {(decision.status === 'decided' || decision.status === 'awaiting_outcome') && !showOutcome && (
                <button
                    onClick={() => setShowOutcome(true)}
                    className="mt-4 btn-primary text-sm"
                >
                    📊 Record Outcome
                </button>
            )}

            {/* Outcome Form */}
            {showOutcome && (
                <div className="mt-4 p-4 bg-surface-800/50 rounded-lg space-y-4 border border-surface-600 animate-fade-in">
                    <h4 className="text-white font-medium">Record Outcome</h4>

                    <textarea
                        value={outcomeData.actual_outcome}
                        onChange={(e) => setOutcomeData(prev => ({ ...prev, actual_outcome: e.target.value }))}
                        placeholder="What actually happened?"
                        className="w-full px-3 py-2 bg-surface-900 border border-surface-600 rounded-lg text-white text-sm"
                        rows={2}
                    />

                    <div className="flex items-center gap-4">
                        <label className="text-surface-300 text-sm">Outcome Rating (1-5):</label>
                        <input
                            type="range" min="1" max="5"
                            value={outcomeData.outcome_rating}
                            onChange={(e) => setOutcomeData(prev => ({ ...prev, outcome_rating: parseInt(e.target.value) }))}
                            className="w-24"
                        />
                        <span className="text-white">{outcomeData.outcome_rating}</span>
                    </div>

                    <div className="flex items-center gap-4">
                        <label className="text-surface-300 text-sm">Matched Expectation (1-5):</label>
                        <input
                            type="range" min="1" max="5"
                            value={outcomeData.expectation_matched}
                            onChange={(e) => setOutcomeData(prev => ({ ...prev, expectation_matched: parseInt(e.target.value) }))}
                            className="w-24"
                        />
                        <span className="text-white">{outcomeData.expectation_matched}</span>
                    </div>

                    <textarea
                        value={outcomeData.lessons}
                        onChange={(e) => setOutcomeData(prev => ({ ...prev, lessons: e.target.value }))}
                        placeholder="What did you learn?"
                        className="w-full px-3 py-2 bg-surface-900 border border-surface-600 rounded-lg text-white text-sm"
                        rows={2}
                    />

                    <div className="flex gap-2">
                        <button
                            onClick={handleRecordOutcome}
                            disabled={loading || !outcomeData.actual_outcome}
                            className="btn-primary text-sm"
                        >
                            {loading ? 'Saving...' : 'Save Outcome'}
                        </button>
                        <button onClick={() => setShowOutcome(false)} className="btn-ghost text-sm">
                            Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

/**
 * Insights Panel
 */
function InsightsPanel({ insights }) {
    if (!insights) return null;

    return (
        <div className="glass rounded-xl p-6 space-y-4">
            <h3 className="text-lg font-semibold text-white">📊 Decision Insights</h3>

            {insights.encouragement && (
                <p className="text-primary-400">{insights.encouragement}</p>
            )}

            {insights.patterns?.successful?.length > 0 && (
                <div>
                    <h4 className="text-emerald-400 text-sm font-medium mb-2">✅ What works:</h4>
                    <ul className="space-y-1">
                        {insights.patterns.successful.map((p, i) => (
                            <li key={i} className="text-surface-300 text-sm">• {p}</li>
                        ))}
                    </ul>
                </div>
            )}

            {insights.patterns?.unsuccessful?.length > 0 && (
                <div>
                    <h4 className="text-orange-400 text-sm font-medium mb-2">⚠️ Watch out for:</h4>
                    <ul className="space-y-1">
                        {insights.patterns.unsuccessful.map((p, i) => (
                            <li key={i} className="text-surface-300 text-sm">• {p}</li>
                        ))}
                    </ul>
                </div>
            )}

            {insights.top_advice?.length > 0 && (
                <div>
                    <h4 className="text-blue-400 text-sm font-medium mb-2">💡 Advice:</h4>
                    <ul className="space-y-1">
                        {insights.top_advice.map((a, i) => (
                            <li key={i} className="text-surface-300 text-sm">• {a}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}

/**
 * Main DecisionReview component
 */
export default function DecisionReview() {
    const [decisions, setDecisions] = useState([]);
    const [dueForReview, setDueForReview] = useState([]);
    const [stats, setStats] = useState(null);
    const [insights, setInsights] = useState(null);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('');
    const [showInsights, setShowInsights] = useState(false);
    const [loadingInsights, setLoadingInsights] = useState(false);

    useEffect(() => {
        fetchData();
    }, [statusFilter]);

    const fetchData = async () => {
        try {
            const filters = {};
            if (statusFilter) filters.status = statusFilter;

            const [decisionsData, dueData, statsData] = await Promise.all([
                decisionsApi.list(filters),
                decisionsApi.dueForReview(),
                decisionsApi.getStats(),
            ]);

            setDecisions(decisionsData);
            setDueForReview(dueData);
            setStats(statsData);
        } catch (err) {
            console.error('Failed to fetch decisions:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateInsights = async () => {
        setLoadingInsights(true);
        try {
            const data = await decisionsApi.getInsights(6);
            setInsights(data);
            setShowInsights(true);
        } catch (err) {
            console.error('Failed to generate insights:', err);
        } finally {
            setLoadingInsights(false);
        }
    };

    const handleOutcomeRecorded = (id, updated) => {
        setDecisions(prev => prev.map(d => d.id === id ? updated : d));
        setDueForReview(prev => prev.filter(d => d.id !== id));
        fetchData();
    };

    const STATUS_TABS = [
        { id: '', label: 'All' },
        { id: 'deliberating', label: '🤔 Deliberating' },
        { id: 'decided', label: '✅ Decided' },
        { id: 'awaiting_outcome', label: '⏳ Awaiting' },
        { id: 'completed', label: '📊 Completed' },
    ];

    return (
        <div className="space-y-6">
            {/* Stats */}
            {stats && (
                <div className="flex flex-wrap gap-4 text-sm">
                    <div className="glass px-4 py-2 rounded-lg">
                        <span className="text-surface-400">Total:</span>{' '}
                        <span className="text-white font-medium">{stats.total}</span>
                    </div>
                    <div className="glass px-4 py-2 rounded-lg">
                        <span className="text-surface-400">Deliberating:</span>{' '}
                        <span className="text-yellow-400 font-medium">{stats.deliberating}</span>
                    </div>
                    <div className="glass px-4 py-2 rounded-lg">
                        <span className="text-surface-400">Awaiting Review:</span>{' '}
                        <span className="text-orange-400 font-medium">{stats.awaiting_outcome}</span>
                    </div>
                    {stats.average_rating && (
                        <div className="glass px-4 py-2 rounded-lg">
                            <span className="text-surface-400">Avg Rating:</span>{' '}
                            <span className="text-emerald-400 font-medium">{stats.average_rating.toFixed(1)}/5</span>
                        </div>
                    )}
                </div>
            )}

            {/* Due for Review Alert */}
            {dueForReview.length > 0 && (
                <div className="glass rounded-xl p-4 border-l-4 border-orange-500 bg-orange-500/10">
                    <div className="flex items-center gap-2">
                        <span className="text-2xl">⏰</span>
                        <div>
                            <p className="text-white font-medium">{dueForReview.length} decision(s) need outcome review</p>
                            <p className="text-surface-300 text-sm">Record what happened to learn from your decisions</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Status Tabs */}
            <div className="flex flex-wrap gap-2">
                {STATUS_TABS.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setStatusFilter(tab.id)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all
                            ${statusFilter === tab.id
                                ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                : 'bg-surface-800 text-surface-300 hover:bg-surface-700'}`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Insights Section */}
            <div className="flex gap-4">
                <button
                    onClick={handleGenerateInsights}
                    disabled={loadingInsights}
                    className="btn-primary"
                >
                    {loadingInsights ? '🔄 Generating...' : '✨ Generate Insights'}
                </button>
            </div>

            {showInsights && insights && <InsightsPanel insights={insights} />}

            {/* Decisions List */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="flex items-center gap-3 text-primary-400">
                        <div className="spinner"></div>
                        <span>Loading decisions...</span>
                    </div>
                </div>
            ) : decisions.length === 0 ? (
                <div className="glass rounded-xl p-12 text-center">
                    <div className="text-4xl mb-3">🎯</div>
                    <p className="text-surface-200">No decisions found. Decisions are created from items marked as "decision" type.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {decisions.map(decision => (
                        <DecisionCard
                            key={decision.id}
                            decision={decision}
                            onRecordOutcome={handleOutcomeRecorded}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
