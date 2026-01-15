import { useState } from 'react';
import { bookmarksApi } from '../api/client';

/**
 * Category and complexity config
 */
const CATEGORY_CONFIG = {
    article: { label: 'Article', icon: '📄', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
    course: { label: 'Course', icon: '🎓', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
    video: { label: 'Video', icon: '🎬', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
    tool: { label: 'Tool', icon: '🔧', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
    reference: { label: 'Reference', icon: '📚', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
    social_post: { label: 'Post', icon: '💬', color: 'bg-pink-500/20 text-pink-400 border-pink-500/30' },
    documentation: { label: 'Docs', icon: '📋', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
    other: { label: 'Other', icon: '📎', color: 'bg-slate-500/20 text-slate-400 border-slate-500/30' },
};

const COMPLEXITY_CONFIG = {
    quick_read: { label: 'Quick', color: 'bg-green-500/20 text-green-400' },
    medium: { label: 'Medium', color: 'bg-yellow-500/20 text-yellow-400' },
    deep_dive: { label: 'Deep', color: 'bg-orange-500/20 text-orange-400' },
    multi_session: { label: 'Multi', color: 'bg-red-500/20 text-red-400' },
};

/**
 * Bookmark card component
 */
export default function BookmarkCard({ bookmark, onUpdate, onDelete }) {
    const [loading, setLoading] = useState(false);
    const [showNotes, setShowNotes] = useState(false);
    const [notes, setNotes] = useState(bookmark.user_notes || '');

    const category = CATEGORY_CONFIG[bookmark.category] || CATEGORY_CONFIG.other;
    const complexity = COMPLEXITY_CONFIG[bookmark.complexity] || COMPLEXITY_CONFIG.medium;

    // Parse tags
    let tags = [];
    try {
        tags = JSON.parse(bookmark.topic_tags || '[]');
    } catch (e) { }

    const handleStartReading = async () => {
        setLoading(true);
        try {
            const updated = await bookmarksApi.startSession(bookmark.id);
            window.open(bookmark.url, '_blank');
            if (onUpdate) onUpdate(bookmark.id, updated);
        } catch (err) {
            console.error('Failed to start session:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleComplete = async () => {
        setLoading(true);
        try {
            const updated = await bookmarksApi.complete(bookmark.id);
            if (onUpdate) onUpdate(bookmark.id, updated);
        } catch (err) {
            console.error('Failed to complete:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {
        setLoading(true);
        try {
            await bookmarksApi.delete(bookmark.id);
            if (onDelete) onDelete(bookmark.id);
        } catch (err) {
            console.error('Failed to delete:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSaveNotes = async () => {
        setLoading(true);
        try {
            const updated = await bookmarksApi.update(bookmark.id, { user_notes: notes });
            if (onUpdate) onUpdate(bookmark.id, updated);
            setShowNotes(false);
        } catch (err) {
            console.error('Failed to save notes:', err);
        } finally {
            setLoading(false);
        }
    };

    const togglePriority = async () => {
        const priorities = ['low', 'medium', 'high'];
        const current = priorities.indexOf(bookmark.priority);
        const next = priorities[(current + 1) % 3];
        setLoading(true);
        try {
            const updated = await bookmarksApi.update(bookmark.id, { priority: next });
            if (onUpdate) onUpdate(bookmark.id, updated);
        } catch (err) {
            console.error('Failed to update priority:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={`card item-enter group ${loading ? 'opacity-50' : ''}`}>
            <div className="flex items-start gap-3">
                {/* Favicon */}
                <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-surface-700/50 shrink-0 overflow-hidden">
                    {bookmark.favicon_url ? (
                        <img src={bookmark.favicon_url} alt="" className="w-6 h-6" onError={(e) => e.target.style.display = 'none'} />
                    ) : (
                        <span className="text-lg">{category.icon}</span>
                    )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <h3 className="text-white font-medium leading-snug truncate">
                        {bookmark.title || bookmark.url}
                    </h3>

                    {/* Meta badges */}
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                        <span className={`badge ${category.color} border`}>
                            {category.icon} {category.label}
                        </span>
                        <span className={`badge ${complexity.color}`}>
                            {complexity.label}
                        </span>
                        {bookmark.estimated_minutes && (
                            <span className="badge bg-surface-700/50 text-surface-200">
                                ⏱️ {bookmark.estimated_minutes} min
                            </span>
                        )}
                        {bookmark.sessions_spent > 0 && (
                            <span className="badge bg-purple-500/20 text-purple-400">
                                📖 {bookmark.sessions_spent}x
                            </span>
                        )}
                        {bookmark.priority === 'high' && (
                            <span className="badge bg-red-500/20 text-red-400">⭐ High</span>
                        )}
                    </div>

                    {/* Tags */}
                    {tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                            {tags.slice(0, 4).map((tag, i) => (
                                <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-surface-700/50 text-surface-300">
                                    {tag}
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Summary */}
                    {bookmark.summary && (
                        <p className="mt-2 text-sm text-surface-300 line-clamp-2">
                            {bookmark.summary}
                        </p>
                    )}

                    {/* Progress bar */}
                    {bookmark.status === 'in_progress' && bookmark.progress_percent > 0 && (
                        <div className="mt-2 h-1 bg-surface-700 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary-500 transition-all"
                                style={{ width: `${bookmark.progress_percent}%` }}
                            />
                        </div>
                    )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <button
                        onClick={handleStartReading}
                        disabled={loading}
                        className="btn-ghost p-2 text-blue-400 hover:bg-blue-500/10"
                        title="Start Reading"
                    >
                        ▶️
                    </button>
                    <button
                        onClick={handleComplete}
                        disabled={loading}
                        className="btn-ghost p-2 text-emerald-400 hover:bg-emerald-500/10"
                        title="Mark Complete"
                    >
                        ✅
                    </button>
                    <button
                        onClick={togglePriority}
                        disabled={loading}
                        className="btn-ghost p-2 text-amber-400 hover:bg-amber-500/10"
                        title="Toggle Priority"
                    >
                        ⭐
                    </button>
                    <button
                        onClick={() => setShowNotes(!showNotes)}
                        disabled={loading}
                        className="btn-ghost p-2 text-surface-300 hover:bg-surface-700"
                        title="Add Notes"
                    >
                        📝
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

            {/* Notes panel */}
            {showNotes && (
                <div className="mt-3 pt-3 border-t border-surface-700 animate-fade-in">
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Add your notes..."
                        className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg 
                            text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 resize-none"
                        rows={3}
                    />
                    <div className="flex gap-2 mt-2">
                        <button onClick={handleSaveNotes} className="btn-primary px-3 py-1 text-sm">
                            Save
                        </button>
                        <button onClick={() => setShowNotes(false)} className="btn-ghost px-2 py-1 text-sm">
                            Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
