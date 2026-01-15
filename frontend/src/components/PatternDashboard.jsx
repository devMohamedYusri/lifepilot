/**
 * PatternDashboard - Main component for pattern recognition insights
 */
import { useState, useEffect } from 'react';
import { patternsApi } from '../api/client';

// Pattern type icons and colors
const PATTERN_TYPES = {
    temporal: { icon: '⏰', color: 'text-blue-400', bg: 'bg-blue-500/20' },
    behavioral: { icon: '📊', color: 'text-purple-400', bg: 'bg-purple-500/20' },
    correlation: { icon: '🔗', color: 'text-green-400', bg: 'bg-green-500/20' },
    anomaly: { icon: '⚠️', color: 'text-amber-400', bg: 'bg-amber-500/20' }
};

const CATEGORIES = {
    productivity: { icon: '✅', label: 'Productivity' },
    energy: { icon: '⚡', label: 'Energy' },
    social: { icon: '👥', label: 'Social' },
    learning: { icon: '📚', label: 'Learning' },
    decisions: { icon: '🎯', label: 'Decisions' }
};

export default function PatternDashboard() {
    const [dashboard, setDashboard] = useState(null);
    const [patterns, setPatterns] = useState([]);
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [selectedPattern, setSelectedPattern] = useState(null);
    const [filters, setFilters] = useState({
        pattern_type: '',
        category: '',
        min_confidence: 0
    });
    const [error, setError] = useState(null);

    // Load initial data
    useEffect(() => {
        loadData();
    }, []);

    // Reload patterns when filters change
    useEffect(() => {
        loadPatterns();
    }, [filters]);

    async function loadData() {
        setLoading(true);
        setError(null);
        try {
            const [dashboardData, insightsData] = await Promise.all([
                patternsApi.getDashboard(),
                patternsApi.getInsights()
            ]);
            setDashboard(dashboardData);
            setInsights(insightsData);
            await loadPatterns();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function loadPatterns() {
        try {
            const data = await patternsApi.list(filters);
            setPatterns(data);
        } catch (err) {
            console.error('Failed to load patterns:', err);
        }
    }

    async function runAnalysis() {
        setAnalyzing(true);
        setError(null);
        try {
            const result = await patternsApi.analyze({ date_range_days: 30 });
            await loadData();
            return result;
        } catch (err) {
            setError(err.message);
        } finally {
            setAnalyzing(false);
        }
    }

    async function submitFeedback(patternId, feedbackType) {
        try {
            await patternsApi.submitFeedback(patternId, { feedback_type: feedbackType });
            await loadPatterns();
        } catch (err) {
            console.error('Failed to submit feedback:', err);
        }
    }

    async function dismissInsight(insightId) {
        try {
            await patternsApi.dismissInsight(insightId);
            setInsights(insights.filter(i => i.id !== insightId));
        } catch (err) {
            console.error('Failed to dismiss insight:', err);
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="spinner w-8 h-8" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white">📊 Pattern Insights</h2>
                    <p className="text-surface-200/70">Discover patterns in your productivity and behavior</p>
                </div>
                <button
                    onClick={runAnalysis}
                    disabled={analyzing}
                    className="px-4 py-2 bg-gradient-to-r from-primary-500 to-accent-500 rounded-xl font-medium text-white hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                >
                    {analyzing ? (
                        <>
                            <div className="spinner w-4 h-4" /> Analyzing...
                        </>
                    ) : (
                        <>🔍 Analyze Patterns</>
                    )}
                </button>
            </div>

            {error && (
                <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400">
                    {error}
                </div>
            )}

            {/* Dashboard Stats */}
            {dashboard && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard
                        label="Total Patterns"
                        value={dashboard.total_patterns}
                        icon="📈"
                    />
                    <StatCard
                        label="Active Patterns"
                        value={dashboard.active_patterns}
                        icon="✨"
                    />
                    <StatCard
                        label="Avg Confidence"
                        value={`${Math.round(dashboard.avg_confidence * 100)}%`}
                        icon="🎯"
                    />
                    <StatCard
                        label="Pending Insights"
                        value={dashboard.pending_insights}
                        icon="💡"
                    />
                </div>
            )}

            {/* Insights Panel */}
            {insights.length > 0 && (
                <div className="glass rounded-xl p-4 border border-white/10">
                    <h3 className="font-semibold text-white mb-3">💡 Active Insights</h3>
                    <div className="space-y-3">
                        {insights.map(insight => (
                            <InsightCard
                                key={insight.id}
                                insight={insight}
                                onDismiss={() => dismissInsight(insight.id)}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="flex flex-wrap gap-3">
                <select
                    value={filters.pattern_type}
                    onChange={e => setFilters({ ...filters, pattern_type: e.target.value })}
                    className="px-3 py-2 bg-surface-700 rounded-lg text-white border border-white/10"
                >
                    <option value="">All Types</option>
                    <option value="temporal">⏰ Temporal</option>
                    <option value="behavioral">📊 Behavioral</option>
                    <option value="correlation">🔗 Correlation</option>
                </select>

                <select
                    value={filters.category}
                    onChange={e => setFilters({ ...filters, category: e.target.value })}
                    className="px-3 py-2 bg-surface-700 rounded-lg text-white border border-white/10"
                >
                    <option value="">All Categories</option>
                    {Object.entries(CATEGORIES).map(([key, { icon, label }]) => (
                        <option key={key} value={key}>{icon} {label}</option>
                    ))}
                </select>

                <select
                    value={filters.min_confidence}
                    onChange={e => setFilters({ ...filters, min_confidence: parseFloat(e.target.value) })}
                    className="px-3 py-2 bg-surface-700 rounded-lg text-white border border-white/10"
                >
                    <option value="0">Any Confidence</option>
                    <option value="0.5">50%+ Confidence</option>
                    <option value="0.7">70%+ Confidence</option>
                    <option value="0.9">90%+ Confidence</option>
                </select>
            </div>

            {/* Patterns List */}
            {patterns.length === 0 ? (
                <div className="glass rounded-xl p-8 text-center border border-white/10">
                    <div className="text-4xl mb-3">🔍</div>
                    <h3 className="text-white font-medium mb-2">No patterns discovered yet</h3>
                    <p className="text-surface-200/70 mb-4">
                        Click "Analyze Patterns" to discover insights from your data.
                    </p>
                    <p className="text-surface-200/50 text-sm">
                        Note: Pattern analysis works best with at least 2 weeks of data.
                    </p>
                </div>
            ) : (
                <div className="grid gap-4">
                    {patterns.map(pattern => (
                        <PatternCard
                            key={pattern.id}
                            pattern={pattern}
                            isSelected={selectedPattern?.id === pattern.id}
                            onClick={() => setSelectedPattern(selectedPattern?.id === pattern.id ? null : pattern)}
                            onFeedback={submitFeedback}
                        />
                    ))}
                </div>
            )}

            {/* Last Analysis */}
            {dashboard?.last_analysis && (
                <p className="text-center text-surface-200/50 text-sm">
                    Last analysis: {new Date(dashboard.last_analysis).toLocaleString()}
                </p>
            )}
        </div>
    );
}

function StatCard({ label, value, icon }) {
    return (
        <div className="glass rounded-xl p-4 border border-white/10 text-center">
            <div className="text-2xl mb-1">{icon}</div>
            <div className="text-2xl font-bold text-white">{value}</div>
            <div className="text-sm text-surface-200/70">{label}</div>
        </div>
    );
}

function InsightCard({ insight, onDismiss }) {
    const typeConfig = {
        recommendation: { icon: '💡', color: 'border-blue-500/30 bg-blue-500/10' },
        warning: { icon: '⚠️', color: 'border-amber-500/30 bg-amber-500/10' },
        achievement: { icon: '🏆', color: 'border-green-500/30 bg-green-500/10' },
        observation: { icon: '👁️', color: 'border-purple-500/30 bg-purple-500/10' }
    };

    const config = typeConfig[insight.insight_type] || typeConfig.observation;

    return (
        <div className={`p-3 rounded-lg border ${config.color}`}>
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2">
                    <span className="text-lg">{config.icon}</span>
                    <div>
                        <h4 className="font-medium text-white">{insight.title}</h4>
                        <p className="text-sm text-surface-200/70">{insight.message}</p>
                        {insight.suggested_action && (
                            <p className="text-sm text-primary-400 mt-1">
                                → {insight.suggested_action}
                            </p>
                        )}
                    </div>
                </div>
                <button
                    onClick={onDismiss}
                    className="text-surface-200/50 hover:text-white text-sm"
                >
                    ✕
                </button>
            </div>
        </div>
    );
}

function PatternCard({ pattern, isSelected, onClick, onFeedback }) {
    const typeConfig = PATTERN_TYPES[pattern.pattern_type] || PATTERN_TYPES.behavioral;
    const categoryConfig = CATEGORIES[pattern.category] || CATEGORIES.productivity;

    return (
        <div
            className={`glass rounded-xl p-4 border border-white/10 cursor-pointer transition-all ${isSelected ? 'ring-2 ring-primary-500' : 'hover:bg-white/5'
                }`}
            onClick={onClick}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-lg ${typeConfig.bg} flex items-center justify-center text-xl`}>
                        {typeConfig.icon}
                    </div>
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${typeConfig.bg} ${typeConfig.color}`}>
                                {pattern.pattern_type}
                            </span>
                            <span className="text-xs text-surface-200/50">
                                {categoryConfig.icon} {categoryConfig.label}
                            </span>
                        </div>
                        <p className="text-white">{pattern.description}</p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-surface-200/50">
                            <span>{pattern.data_points} data points</span>
                            <span>
                                Discovered {new Date(pattern.first_discovered).toLocaleDateString()}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Confidence Bar */}
                <div className="text-right min-w-[80px]">
                    <div className="text-sm font-medium text-white">
                        {Math.round(pattern.confidence * 100)}%
                    </div>
                    <div className="w-full h-2 bg-surface-700 rounded-full mt-1 overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                            style={{ width: `${pattern.confidence * 100}%` }}
                        />
                    </div>
                    <div className="text-xs text-surface-200/50 mt-0.5">confidence</div>
                </div>
            </div>

            {/* Expanded Details */}
            {isSelected && (
                <div className="mt-4 pt-4 border-t border-white/10">
                    {pattern.pattern_data && (
                        <div className="mb-3 p-3 bg-surface-800 rounded-lg">
                            <div className="text-xs text-surface-200/50 mb-1">Pattern Details</div>
                            <pre className="text-sm text-surface-200 overflow-auto">
                                {JSON.stringify(pattern.pattern_data, null, 2)}
                            </pre>
                        </div>
                    )}

                    <div className="flex items-center gap-2">
                        <span className="text-sm text-surface-200/70">Rate this pattern:</span>
                        <button
                            onClick={(e) => { e.stopPropagation(); onFeedback(pattern.id, 'accurate'); }}
                            className="px-3 py-1 text-sm bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30"
                        >
                            ✓ Accurate
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); onFeedback(pattern.id, 'inaccurate'); }}
                            className="px-3 py-1 text-sm bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30"
                        >
                            ✗ Inaccurate
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); onFeedback(pattern.id, 'helpful'); }}
                            className="px-3 py-1 text-sm bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30"
                        >
                            👍 Helpful
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
