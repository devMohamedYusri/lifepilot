import { useState, useEffect } from 'react';
import { energyApi } from '../api/client';

/**
 * Energy Dashboard - Track and analyze energy patterns
 */
export default function EnergyDashboard() {
    const [stats, setStats] = useState(null);
    const [logs, setLogs] = useState([]);
    const [patterns, setPatterns] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showQuickLog, setShowQuickLog] = useState(false);
    const [showFullLog, setShowFullLog] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [statsData, logsData] = await Promise.all([
                energyApi.stats(),
                energyApi.getLogs(7)
            ]);
            setStats(statsData);
            setLogs(logsData.logs || []);
        } catch (err) {
            console.error('Failed to fetch energy data:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchPatterns = async () => {
        try {
            const data = await energyApi.patterns();
            setPatterns(data);
        } catch (err) {
            console.error('Failed to fetch patterns:', err);
        }
    };

    const handleQuickLog = async (energy, focus) => {
        try {
            await energyApi.quickLog(energy, focus);
            setShowQuickLog(false);
            fetchData();
        } catch (err) {
            console.error('Failed to log energy:', err);
        }
    };

    const handleFullLog = async (logData) => {
        try {
            await energyApi.log(logData);
            setShowFullLog(false);
            fetchData();
        } catch (err) {
            console.error('Failed to log energy:', err);
        }
    };

    const energyEmojis = ['😫', '😕', '😐', '🙂', '😄'];
    const timeBlockColors = {
        morning: 'bg-amber-500/20 text-amber-400',
        midday: 'bg-yellow-500/20 text-yellow-400',
        afternoon: 'bg-orange-500/20 text-orange-400',
        evening: 'bg-purple-500/20 text-purple-400',
        night: 'bg-blue-500/20 text-blue-400'
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="flex items-center gap-3 text-primary-400">
                    <div className="spinner"></div>
                    <span>Loading energy data...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white">⚡ Energy & Focus</h2>
                    <p className="text-surface-300">Track your energy patterns to optimize productivity</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={() => setShowQuickLog(true)} className="btn-primary">
                        ⚡ Quick Log
                    </button>
                    <button onClick={() => setShowFullLog(true)} className="px-4 py-2 glass rounded-lg text-white hover:bg-white/10">
                        📝 Full Log
                    </button>
                </div>
            </div>

            {/* Today's Stats */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="glass rounded-xl p-4 text-center">
                        <div className="text-3xl mb-1">
                            {stats.today?.averages?.energy ? energyEmojis[Math.round(stats.today.averages.energy) - 1] : '—'}
                        </div>
                        <div className="text-lg font-bold text-primary-400">
                            {stats.today?.averages?.energy?.toFixed(1) || '—'}
                        </div>
                        <div className="text-surface-300 text-sm">Today's Energy</div>
                    </div>
                    <div className="glass rounded-xl p-4 text-center">
                        <div className="text-3xl mb-1">🎯</div>
                        <div className="text-lg font-bold text-blue-400">
                            {stats.today?.averages?.focus?.toFixed(1) || '—'}
                        </div>
                        <div className="text-surface-300 text-sm">Today's Focus</div>
                    </div>
                    <div className="glass rounded-xl p-4 text-center">
                        <div className="text-3xl mb-1">📊</div>
                        <div className="text-lg font-bold text-emerald-400">
                            {stats.today?.logs_count || 0}
                        </div>
                        <div className="text-surface-300 text-sm">Logs Today</div>
                    </div>
                    <div className="glass rounded-xl p-4 text-center">
                        <div className="text-3xl mb-1">⏰</div>
                        <div className="text-lg font-bold text-amber-400 capitalize">
                            {stats.today?.current_block || 'morning'}
                        </div>
                        <div className="text-surface-300 text-sm">Current Block</div>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Recent Logs */}
                <div className="lg:col-span-2">
                    <div className="glass rounded-xl p-6">
                        <h3 className="text-lg font-semibold text-white mb-4">📈 Recent Logs</h3>
                        {logs.length === 0 ? (
                            <div className="text-center py-8">
                                <div className="text-5xl mb-4">⚡</div>
                                <p className="text-surface-300 mb-4">No energy logs yet. Start tracking!</p>
                                <button onClick={() => setShowQuickLog(true)} className="btn-primary">
                                    Log Your First Entry
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {logs.slice(0, 10).map(log => (
                                    <div key={log.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-white/5">
                                        <div className="text-2xl">
                                            {energyEmojis[(log.energy_level || 3) - 1]}
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className="text-white font-medium">Energy: {log.energy_level}/5</span>
                                                {log.focus_level && <span className="text-surface-400">• Focus: {log.focus_level}/5</span>}
                                                <span className={`px-2 py-0.5 rounded text-xs ${timeBlockColors[log.time_block] || 'bg-surface-600'}`}>
                                                    {log.time_block}
                                                </span>
                                            </div>
                                            <div className="text-surface-400 text-sm">
                                                {new Date(log.logged_at).toLocaleString()}
                                                {log.notes && ` — ${log.notes}`}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Insights Panel */}
                <div className="space-y-4">
                    {/* Time Block Averages */}
                    {stats?.week?.by_time_block && Object.keys(stats.week.by_time_block).length > 0 && (
                        <div className="glass rounded-xl p-4">
                            <h3 className="text-white font-semibold mb-3">🕐 By Time of Day</h3>
                            <div className="space-y-2">
                                {Object.entries(stats.week.by_time_block).map(([block, data]) => (
                                    <div key={block} className="flex items-center justify-between">
                                        <span className={`px-2 py-0.5 rounded text-xs capitalize ${timeBlockColors[block]}`}>
                                            {block}
                                        </span>
                                        <div className="flex items-center gap-2">
                                            <span className="text-white">{data.avg_energy?.toFixed(1) || '—'}</span>
                                            <div className="w-16 h-2 bg-surface-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-primary-500 rounded-full"
                                                    style={{ width: `${((data.avg_energy || 0) / 5) * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Insights */}
                    {stats?.insights?.peak_time && (
                        <div className="glass rounded-xl p-4">
                            <h3 className="text-white font-semibold mb-3">💡 Insights</h3>
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-surface-300">Peak Energy</span>
                                    <span className="text-emerald-400 capitalize">{stats.insights.peak_time}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-surface-300">Low Energy</span>
                                    <span className="text-amber-400 capitalize">{stats.insights.low_time}</span>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Patterns Button */}
                    <div className="glass rounded-xl p-4">
                        <button
                            onClick={fetchPatterns}
                            className="w-full btn-primary"
                            disabled={!stats?.has_enough_data}
                        >
                            ✨ Analyze Patterns
                        </button>
                        {!stats?.has_enough_data && (
                            <p className="text-surface-400 text-xs mt-2 text-center">
                                Log at least 5 entries to unlock patterns
                            </p>
                        )}
                    </div>

                    {/* Patterns Display */}
                    {patterns && (
                        <div className="glass rounded-xl p-4">
                            <h3 className="text-white font-semibold mb-3">🔮 AI Patterns</h3>
                            {patterns.message ? (
                                <p className="text-surface-300 text-sm">{patterns.message}</p>
                            ) : (
                                <div className="space-y-3 text-sm">
                                    {patterns.insight && (
                                        <p className="text-primary-400">{patterns.insight}</p>
                                    )}
                                    {patterns.recommendations?.slice(0, 3).map((rec, i) => (
                                        <div key={i} className="flex items-start gap-2">
                                            <span className="text-emerald-400">•</span>
                                            <span className="text-surface-200">{rec}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Quick Log Modal */}
            {showQuickLog && (
                <QuickLogModal
                    onClose={() => setShowQuickLog(false)}
                    onLog={handleQuickLog}
                />
            )}

            {/* Full Log Modal */}
            {showFullLog && (
                <FullLogModal
                    onClose={() => setShowFullLog(false)}
                    onLog={handleFullLog}
                />
            )}
        </div>
    );
}

/**
 * Quick Log Modal - Just energy + focus
 */
function QuickLogModal({ onClose, onLog }) {
    const [energy, setEnergy] = useState(3);
    const [focus, setFocus] = useState(3);

    const energyEmojis = ['😫', '😕', '😐', '🙂', '😄'];
    const energyLabels = ['Very Low', 'Low', 'Okay', 'Good', 'Great'];

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="glass rounded-2xl p-6 max-w-sm w-full">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-white">⚡ Quick Check-in</h2>
                    <button onClick={onClose} className="text-surface-400 hover:text-white">✕</button>
                </div>

                <div className="space-y-6">
                    {/* Energy Slider */}
                    <div>
                        <label className="text-surface-300 text-sm block mb-3">How's your energy?</label>
                        <div className="flex justify-between gap-2">
                            {[1, 2, 3, 4, 5].map(level => (
                                <button
                                    key={level}
                                    onClick={() => setEnergy(level)}
                                    className={`flex-1 py-3 rounded-lg text-2xl transition-all ${energy === level
                                            ? 'bg-primary-500/30 ring-2 ring-primary-400'
                                            : 'bg-surface-700 hover:bg-surface-600'
                                        }`}
                                >
                                    {energyEmojis[level - 1]}
                                </button>
                            ))}
                        </div>
                        <div className="text-center mt-2 text-primary-400">{energyLabels[energy - 1]}</div>
                    </div>

                    {/* Focus Slider */}
                    <div>
                        <label className="text-surface-300 text-sm block mb-3">Focus level?</label>
                        <div className="flex justify-between gap-2">
                            {[1, 2, 3, 4, 5].map(level => (
                                <button
                                    key={level}
                                    onClick={() => setFocus(level)}
                                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${focus === level
                                            ? 'bg-blue-500/30 ring-2 ring-blue-400 text-blue-400'
                                            : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                                        }`}
                                >
                                    {level}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex gap-3 mt-6">
                    <button onClick={onClose} className="flex-1 px-4 py-2 text-surface-300 hover:bg-white/5 rounded-lg">
                        Cancel
                    </button>
                    <button onClick={() => onLog(energy, focus)} className="flex-1 btn-primary">
                        Log
                    </button>
                </div>
            </div>
        </div>
    );
}

/**
 * Full Log Modal - All fields
 */
function FullLogModal({ onClose, onLog }) {
    const [formData, setFormData] = useState({
        energy_level: 3,
        focus_level: 3,
        mood_level: 3,
        stress_level: 2,
        sleep_hours: '',
        caffeine: 0,
        exercise: 0,
        current_activity: '',
        location: '',
        notes: ''
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        onLog(formData);
    };

    const energyEmojis = ['😫', '😕', '😐', '🙂', '😄'];

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="glass rounded-2xl p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-white">📝 Full Energy Log</h2>
                    <button onClick={onClose} className="text-surface-400 hover:text-white">✕</button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Energy */}
                    <div>
                        <label className="text-surface-300 text-sm block mb-2">Energy Level *</label>
                        <div className="flex justify-between gap-2">
                            {[1, 2, 3, 4, 5].map(level => (
                                <button
                                    key={level}
                                    type="button"
                                    onClick={() => setFormData(prev => ({ ...prev, energy_level: level }))}
                                    className={`flex-1 py-2 rounded-lg text-xl ${formData.energy_level === level
                                            ? 'bg-primary-500/30 ring-2 ring-primary-400'
                                            : 'bg-surface-700'
                                        }`}
                                >
                                    {energyEmojis[level - 1]}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Focus & Mood */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-surface-300 text-sm block mb-2">Focus</label>
                            <select
                                value={formData.focus_level}
                                onChange={(e) => setFormData(prev => ({ ...prev, focus_level: parseInt(e.target.value) }))}
                                className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            >
                                {[1, 2, 3, 4, 5].map(v => <option key={v} value={v}>{v} - {['Very Low', 'Low', 'Medium', 'High', 'Very High'][v - 1]}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="text-surface-300 text-sm block mb-2">Mood</label>
                            <select
                                value={formData.mood_level}
                                onChange={(e) => setFormData(prev => ({ ...prev, mood_level: parseInt(e.target.value) }))}
                                className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            >
                                {[1, 2, 3, 4, 5].map(v => <option key={v} value={v}>{v} - {['Bad', 'Low', 'Okay', 'Good', 'Great'][v - 1]}</option>)}
                            </select>
                        </div>
                    </div>

                    {/* Sleep & Caffeine */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-surface-300 text-sm block mb-2">Sleep (hours)</label>
                            <input
                                type="number"
                                step="0.5"
                                value={formData.sleep_hours}
                                onChange={(e) => setFormData(prev => ({ ...prev, sleep_hours: parseFloat(e.target.value) || '' }))}
                                className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                                placeholder="7.5"
                            />
                        </div>
                        <div>
                            <label className="text-surface-300 text-sm block mb-2">Caffeine (cups)</label>
                            <input
                                type="number"
                                value={formData.caffeine}
                                onChange={(e) => setFormData(prev => ({ ...prev, caffeine: parseInt(e.target.value) || 0 }))}
                                className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            />
                        </div>
                    </div>

                    {/* Notes */}
                    <div>
                        <label className="text-surface-300 text-sm block mb-2">Notes</label>
                        <textarea
                            value={formData.notes}
                            onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                            className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            rows={2}
                            placeholder="How are you feeling?"
                        />
                    </div>

                    <div className="flex gap-3 pt-4">
                        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 text-surface-300 hover:bg-white/5 rounded-lg">
                            Cancel
                        </button>
                        <button type="submit" className="flex-1 btn-primary">
                            Log Entry
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
