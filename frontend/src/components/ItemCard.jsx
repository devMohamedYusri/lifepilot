import { useState } from 'react';
import { itemsApi, decisionsApi } from '../api/client';

/**
 * Type labels and icons
 */
const TYPE_CONFIG = {
    task: { label: 'Task', icon: '✓', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
    waiting_for: { label: 'Waiting', icon: '⏳', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
    decision: { label: 'Decision', icon: '🤔', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
    note: { label: 'Note', icon: '📝', color: 'bg-slate-500/20 text-slate-400 border-slate-500/30' },
    life_admin: { label: 'Life Admin', icon: '🏠', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
};

const PRIORITY_CONFIG = {
    high: { label: 'High', class: 'badge-high' },
    medium: { label: 'Med', class: 'badge-medium' },
    low: { label: 'Low', class: 'badge-low' },
};

/**
 * Individual item card with Phase 2 features
 */
export default function ItemCard({ item, onUpdate, onDelete, needsFollowup = false }) {
    const [loading, setLoading] = useState(false);
    const [showSnooze, setShowSnooze] = useState(false);
    const [showFollowUp, setShowFollowUp] = useState(false);
    const [snoozeDate, setSnoozeDate] = useState('');
    const [followUpNote, setFollowUpNote] = useState('');
    const [expanding, setExpanding] = useState(false);
    const [expanded, setExpanded] = useState(false);

    const typeConfig = TYPE_CONFIG[item.type] || TYPE_CONFIG.note;
    const priorityConfig = PRIORITY_CONFIG[item.priority] || PRIORITY_CONFIG.medium;

    // Handle expand decision
    const handleExpandDecision = async () => {
        setExpanding(true);
        try {
            await decisionsApi.expand(item.id);
            setExpanded(true);
            // Show success message
        } catch (err) {
            if (err.message?.includes('already expanded')) {
                setExpanded(true);
            }
            console.error('Failed to expand decision:', err);
        } finally {
            setExpanding(false);
        }
    };

    const handleDone = async () => {
        setLoading(true);
        try {
            await itemsApi.update(item.id, { status: 'done' });
            if (onUpdate) onUpdate(item.id, { status: 'done' });
        } catch (err) {
            console.error('Failed to mark done:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {
        setLoading(true);
        try {
            await itemsApi.delete(item.id);
            if (onDelete) onDelete(item.id);
        } catch (err) {
            console.error('Failed to delete:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSnooze = async () => {
        if (!snoozeDate) return;
        setLoading(true);
        try {
            await itemsApi.update(item.id, { snoozed_until: snoozeDate });
            if (onUpdate) onUpdate(item.id, { snoozed_until: snoozeDate });
            setShowSnooze(false);
            setSnoozeDate('');
        } catch (err) {
            console.error('Failed to snooze:', err);
        } finally {
            setLoading(false);
        }
    };

    // Phase 2: Handle follow-up
    const handleFollowUp = async () => {
        setLoading(true);
        try {
            const updated = await itemsApi.followUp(item.id, followUpNote || null);
            if (onUpdate) onUpdate(item.id, updated);
            setShowFollowUp(false);
            setFollowUpNote('');
        } catch (err) {
            console.error('Failed to record follow-up:', err);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return null;
        const date = new Date(dateStr);
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        if (date.toDateString() === today.toDateString()) return 'Today';
        if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow';

        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    const isOverdue = item.due_date && new Date(item.due_date) < new Date() && item.status !== 'done';

    return (
        <div className={`card item-enter group ${loading ? 'opacity-50' : ''}`}>
            <div className="flex items-start gap-3">
                {/* Type icon */}
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg
                        ${typeConfig.color} border shrink-0`}>
                    {typeConfig.icon}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                        <h3 className="text-white font-medium leading-snug">
                            {item.ai_summary || item.raw_content}
                        </h3>
                    </div>

                    {/* Meta info */}
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                        <span className={`badge ${typeConfig.color} border`}>
                            {typeConfig.label}
                        </span>
                        <span className={`badge ${priorityConfig.class}`}>
                            {priorityConfig.label}
                        </span>
                        {item.context && (
                            <span className="badge bg-surface-700/50 text-surface-200 border border-surface-600">
                                {item.context}
                            </span>
                        )}
                        {item.due_date && (
                            <span className={`badge ${isOverdue
                                ? 'bg-red-500/20 text-red-400 border-red-500/30'
                                : 'bg-surface-700/50 text-surface-200 border-surface-600'}`}>
                                📅 {formatDate(item.due_date)}
                            </span>
                        )}
                        {item.person_involved && (
                            <span className="badge bg-surface-700/50 text-surface-200 border border-surface-600">
                                👤 {item.person_involved}
                            </span>
                        )}
                        {/* Phase 2: Needs Follow-up Badge */}
                        {needsFollowup && (
                            <span className="badge bg-red-500/20 text-red-400 border-red-500/30 animate-pulse">
                                🔔 Needs Follow-up
                            </span>
                        )}
                        {/* Phase 2: Follow-up count */}
                        {item.follow_up_count > 0 && (
                            <span className="badge bg-purple-500/20 text-purple-400 border-purple-500/30">
                                📞 Followed up {item.follow_up_count}x
                            </span>
                        )}
                        {/* Phase 2: Recurrence badge */}
                        {item.recurrence_pattern && (
                            <span className="badge bg-cyan-500/20 text-cyan-400 border-cyan-500/30">
                                🔁 {item.recurrence_pattern}
                            </span>
                        )}
                    </div>

                    {/* Next action */}
                    {item.ai_next_action && (
                        <p className="mt-2 text-sm text-primary-400/80 italic">
                            → {item.ai_next_action}
                        </p>
                    )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <button
                        onClick={handleDone}
                        disabled={loading}
                        className="btn-ghost p-2 text-emerald-400 hover:bg-emerald-500/10"
                        title="Mark as done"
                    >
                        ✓
                    </button>
                    {/* Phase 2: Follow-up button for waiting_for */}
                    {item.type === 'waiting_for' && (
                        <button
                            onClick={() => setShowFollowUp(!showFollowUp)}
                            disabled={loading}
                            className="btn-ghost p-2 text-purple-400 hover:bg-purple-500/10"
                            title="I followed up"
                        >
                            📞
                        </button>
                    )}
                    {/* Phase 2A: Expand decision button */}
                    {item.type === 'decision' && !expanded && (
                        <button
                            onClick={handleExpandDecision}
                            disabled={expanding}
                            className="btn-ghost p-2 text-amber-400 hover:bg-amber-500/10"
                            title="Expand to Decision Journal"
                        >
                            {expanding ? '⏳' : '📝'}
                        </button>
                    )}
                    {item.type === 'decision' && expanded && (
                        <span
                            className="p-2 text-emerald-400"
                            title="Expanded in Decisions tab"
                        >
                            ✓ Expanded
                        </span>
                    )}
                    <button
                        onClick={() => setShowSnooze(!showSnooze)}
                        disabled={loading}
                        className="btn-ghost p-2 text-amber-400 hover:bg-amber-500/10"
                        title="Snooze"
                    >
                        😴
                    </button>
                    <button
                        onClick={handleDelete}
                        disabled={loading}
                        className="btn-ghost p-2 text-red-400 hover:bg-red-500/10"
                        title="Delete"
                    >
                        🗑️
                    </button>
                </div>
            </div>

            {/* Snooze picker */}
            {showSnooze && (
                <div className="mt-3 pt-3 border-t border-surface-700 flex items-center gap-2 animate-fade-in">
                    <span className="text-sm text-surface-200">Snooze until:</span>
                    <input
                        type="date"
                        value={snoozeDate}
                        onChange={(e) => setSnoozeDate(e.target.value)}
                        min={new Date().toISOString().split('T')[0]}
                        className="px-3 py-1.5 bg-surface-800 border border-surface-600 rounded-lg 
                     text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                    />
                    <button
                        onClick={handleSnooze}
                        disabled={!snoozeDate || loading}
                        className="btn-primary px-3 py-1.5 text-sm"
                    >
                        Snooze
                    </button>
                    <button
                        onClick={() => { setShowSnooze(false); setSnoozeDate(''); }}
                        className="btn-ghost px-2 py-1 text-sm"
                    >
                        Cancel
                    </button>
                </div>
            )}

            {/* Phase 2: Follow-up modal */}
            {showFollowUp && (
                <div className="mt-3 pt-3 border-t border-surface-700 flex items-center gap-2 animate-fade-in">
                    <span className="text-sm text-surface-200">Note:</span>
                    <input
                        type="text"
                        value={followUpNote}
                        onChange={(e) => setFollowUpNote(e.target.value)}
                        placeholder="Optional follow-up note..."
                        className="flex-1 px-3 py-1.5 bg-surface-800 border border-surface-600 rounded-lg 
                     text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                    />
                    <button
                        onClick={handleFollowUp}
                        disabled={loading}
                        className="btn-primary px-3 py-1.5 text-sm"
                    >
                        Followed Up
                    </button>
                    <button
                        onClick={() => { setShowFollowUp(false); setFollowUpNote(''); }}
                        className="btn-ghost px-2 py-1 text-sm"
                    >
                        Cancel
                    </button>
                </div>
            )}
        </div>
    );
}

