import { useState, useEffect, useMemo } from 'react';
import { bookmarksApi } from '../api/client';
import BookmarkCard from './BookmarkCard';

/**
 * Reading Queue component with time/energy selectors
 */
function ReadingQueue({ onStartReading }) {
    const [minutes, setMinutes] = useState(30);
    const [energy, setEnergy] = useState('medium');
    const [queue, setQueue] = useState(null);
    const [loading, setLoading] = useState(false);

    const generateQueue = async () => {
        setLoading(true);
        try {
            const result = await bookmarksApi.getReadingQueue(minutes, energy);
            setQueue(result);
        } catch (err) {
            console.error('Failed to generate queue:', err);
        } finally {
            setLoading(false);
        }
    };

    if (!queue) {
        return (
            <div className="glass rounded-xl p-6 mb-6">
                <h3 className="text-lg font-semibold text-white mb-4">📖 Reading Queue</h3>
                <div className="flex flex-wrap items-center gap-4 mb-4">
                    <div className="flex items-center gap-2">
                        <span className="text-surface-200 text-sm">I have</span>
                        <input
                            type="number"
                            value={minutes}
                            onChange={(e) => setMinutes(Math.max(5, parseInt(e.target.value) || 30))}
                            className="w-16 px-2 py-1 bg-surface-800 border border-surface-600 rounded text-white text-center"
                            min={5}
                            max={480}
                        />
                        <span className="text-surface-200 text-sm">minutes</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-surface-200 text-sm">Energy:</span>
                        {['low', 'medium', 'high'].map((e) => (
                            <button
                                key={e}
                                onClick={() => setEnergy(e)}
                                className={`px-3 py-1 rounded ${energy === e
                                    ? 'bg-primary-500 text-white'
                                    : 'bg-surface-700 text-surface-300 hover:bg-surface-600'}`}
                            >
                                {e.charAt(0).toUpperCase() + e.slice(1)}
                            </button>
                        ))}
                    </div>
                    <button
                        onClick={generateQueue}
                        disabled={loading}
                        className="btn-primary"
                    >
                        {loading ? 'Generating...' : '✨ Generate Queue'}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="glass rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">📖 Your Reading Queue</h3>
                <button
                    onClick={() => setQueue(null)}
                    className="btn-ghost text-sm"
                >
                    Regenerate
                </button>
            </div>

            {queue.encouragement && (
                <p className="text-primary-400 text-sm mb-4">{queue.encouragement}</p>
            )}

            <div className="space-y-3">
                {queue.queue?.map((item, i) => {
                    const bookmark = queue.bookmarks?.find(b => b.id === item.id);
                    if (!bookmark) return null;
                    return (
                        <div key={item.id} className="flex items-center gap-3 p-3 bg-surface-800/50 rounded-lg">
                            <span className="text-2xl font-bold text-primary-500">{i + 1}</span>
                            <div className="flex-1 min-w-0">
                                <p className="text-white font-medium truncate">{bookmark.title}</p>
                                <p className="text-sm text-surface-300">{item.reason}</p>
                            </div>
                            <span className="text-sm text-surface-400">⏱️ {bookmark.estimated_minutes} min</span>
                            <button
                                onClick={() => {
                                    window.open(bookmark.url, '_blank');
                                    bookmarksApi.startSession(bookmark.id);
                                }}
                                className="btn-primary px-3 py-1 text-sm"
                            >
                                Start
                            </button>
                        </div>
                    );
                })}
            </div>

            {queue.total_time > 0 && (
                <p className="text-surface-400 text-sm mt-4">
                    Total estimated time: {queue.total_time} minutes
                </p>
            )}
        </div>
    );
}

/**
 * Main Bookmark Manager component
 */
export default function BookmarkManager() {
    const [bookmarks, setBookmarks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [newUrl, setNewUrl] = useState('');
    const [adding, setAdding] = useState(false);
    const [stats, setStats] = useState(null);

    // Filters
    const [statusFilter, setStatusFilter] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        fetchBookmarks();
        fetchStats();
    }, [statusFilter, categoryFilter, searchQuery]);

    const fetchBookmarks = async () => {
        try {
            const filters = {};
            if (statusFilter) filters.status = statusFilter;
            if (categoryFilter) filters.category = categoryFilter;
            if (searchQuery) filters.search = searchQuery;

            const data = await bookmarksApi.list(filters);
            setBookmarks(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const fetchStats = async () => {
        try {
            const data = await bookmarksApi.getStats();
            setStats(data);
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
    };

    const handleAddBookmark = async (e) => {
        e.preventDefault();
        if (!newUrl.trim()) return;

        setAdding(true);
        try {
            const bookmark = await bookmarksApi.create(newUrl.trim());
            setBookmarks(prev => [bookmark, ...prev]);
            setNewUrl('');
            fetchStats();
        } catch (err) {
            setError(err.message);
        } finally {
            setAdding(false);
        }
    };

    const handleUpdate = (id, updated) => {
        setBookmarks(prev => prev.map(b => b.id === id ? { ...b, ...updated } : b));
        fetchStats();
    };

    const handleDelete = (id) => {
        setBookmarks(prev => prev.filter(b => b.id !== id));
        fetchStats();
    };

    return (
        <div className="space-y-6">
            {/* Stats bar */}
            {stats && (
                <div className="flex flex-wrap gap-4 text-sm">
                    <div className="glass px-4 py-2 rounded-lg">
                        <span className="text-surface-400">Unread:</span>{' '}
                        <span className="text-white font-medium">{stats.unread}</span>
                    </div>
                    <div className="glass px-4 py-2 rounded-lg">
                        <span className="text-surface-400">In Progress:</span>{' '}
                        <span className="text-amber-400 font-medium">{stats.in_progress}</span>
                    </div>
                    <div className="glass px-4 py-2 rounded-lg">
                        <span className="text-surface-400">Completed:</span>{' '}
                        <span className="text-emerald-400 font-medium">{stats.completed}</span>
                    </div>
                    <div className="glass px-4 py-2 rounded-lg">
                        <span className="text-surface-400">Time saved:</span>{' '}
                        <span className="text-primary-400 font-medium">{stats.total_completed_minutes} min</span>
                    </div>
                </div>
            )}

            {/* URL Input */}
            <form onSubmit={handleAddBookmark} className="glass rounded-xl p-4">
                <div className="flex gap-3">
                    <input
                        type="url"
                        value={newUrl}
                        onChange={(e) => setNewUrl(e.target.value)}
                        placeholder="Paste a URL to save..."
                        className="flex-1 px-4 py-3 bg-surface-800 border border-surface-600 rounded-lg
                            text-white placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                        disabled={adding}
                    />
                    <button
                        type="submit"
                        disabled={adding || !newUrl.trim()}
                        className="btn-primary px-6"
                    >
                        {adding ? '🔄 Analyzing...' : '📌 Save'}
                    </button>
                </div>
            </form>

            {/* Reading Queue */}
            <ReadingQueue />

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                >
                    <option value="">All Status</option>
                    <option value="unread">Unread</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="archived">Archived</option>
                </select>

                <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                >
                    <option value="">All Categories</option>
                    <option value="article">Article</option>
                    <option value="video">Video</option>
                    <option value="course">Course</option>
                    <option value="tool">Tool</option>
                    <option value="documentation">Documentation</option>
                    <option value="social_post">Social Post</option>
                </select>

                <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search..."
                    className="px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white placeholder-surface-400"
                />
            </div>

            {/* Error */}
            {error && (
                <div className="px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
                    ⚠️ {error}
                </div>
            )}

            {/* Bookmark list */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="flex items-center gap-3 text-primary-400">
                        <div className="spinner"></div>
                        <span>Loading bookmarks...</span>
                    </div>
                </div>
            ) : bookmarks.length === 0 ? (
                <div className="glass rounded-xl p-12 text-center">
                    <div className="text-4xl mb-3">📚</div>
                    <p className="text-surface-200">No bookmarks yet. Paste a URL above to get started!</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {bookmarks.map(bookmark => (
                        <BookmarkCard
                            key={bookmark.id}
                            bookmark={bookmark}
                            onUpdate={handleUpdate}
                            onDelete={handleDelete}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
