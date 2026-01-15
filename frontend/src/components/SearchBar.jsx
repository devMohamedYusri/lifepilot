import { useState, useEffect, useRef } from 'react';
import { searchApi } from '../api/client';

/**
 * Type icons for search results
 */
const TYPE_ICONS = {
    item: '📋',
    bookmark: '🔖',
    decision: '🎯',
};

/**
 * SearchBar component with Cmd/Ctrl+K shortcut
 */
export default function SearchBar({ onNavigate }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [showResults, setShowResults] = useState(false);
    const [typeFilter, setTypeFilter] = useState(null);
    const inputRef = useRef(null);

    // Keyboard shortcut: Cmd/Ctrl + K
    useEffect(() => {
        const handleKeyDown = (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                inputRef.current?.focus();
                setShowResults(true);
            }
            if (e.key === 'Escape') {
                setShowResults(false);
                inputRef.current?.blur();
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, []);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        try {
            const types = typeFilter ? [typeFilter] : null;
            const data = await searchApi.search(query.trim(), types);
            setResults(data);
            setShowResults(true);
        } catch (err) {
            console.error('Search failed:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleResultClick = (result) => {
        setShowResults(false);
        if (onNavigate) {
            // Map result type to tab
            const tabMap = {
                item: 'tasks',
                bookmark: 'bookmarks',
                decision: 'decisions',
            };
            onNavigate(tabMap[result.type] || 'tasks', result.id);
        }
    };

    const TYPE_FILTERS = [
        { id: null, label: 'All' },
        { id: 'items', label: '📋 Tasks' },
        { id: 'bookmarks', label: '🔖 Bookmarks' },
        { id: 'decisions', label: '🎯 Decisions' },
    ];

    return (
        <div className="relative">
            {/* Search Input */}
            <form onSubmit={handleSearch} className="flex items-center gap-2">
                <div className="relative">
                    <input
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onFocus={() => setShowResults(true)}
                        placeholder="Search... (Ctrl+K)"
                        className="w-64 px-4 py-2 pl-10 bg-surface-800/80 border border-surface-600 rounded-lg
                            text-white text-sm placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                    />
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">🔍</span>
                </div>
                {loading && <span className="text-primary-400 text-sm">Searching...</span>}
            </form>

            {/* Results Dropdown */}
            {showResults && (results || query) && (
                <div className="absolute top-full left-0 right-0 mt-2 glass rounded-xl border border-surface-600 
                    shadow-xl z-50 max-h-96 overflow-y-auto min-w-[400px]"
                    style={{ maxWidth: '600px' }}
                >
                    {/* Type Filters */}
                    <div className="flex gap-1 p-2 border-b border-surface-700">
                        {TYPE_FILTERS.map(f => (
                            <button
                                key={f.id || 'all'}
                                onClick={() => setTypeFilter(f.id)}
                                className={`px-3 py-1 rounded text-xs font-medium transition-all
                                    ${typeFilter === f.id
                                        ? 'bg-primary-500/20 text-primary-400'
                                        : 'bg-surface-700 text-surface-300 hover:bg-surface-600'}`}
                            >
                                {f.label}
                            </button>
                        ))}
                    </div>

                    {/* Interpreted Query */}
                    {results?.interpreted_as && (
                        <p className="px-4 py-2 text-xs text-surface-400 border-b border-surface-700">
                            Searching: {results.interpreted_as}
                        </p>
                    )}

                    {/* Results List */}
                    {results?.results?.length > 0 ? (
                        <div className="divide-y divide-surface-700">
                            {results.results.map((result) => (
                                <button
                                    key={`${result.type}-${result.id}`}
                                    onClick={() => handleResultClick(result)}
                                    className="w-full px-4 py-3 flex items-start gap-3 hover:bg-surface-700/50 
                                        text-left transition-colors"
                                >
                                    <span className="text-xl">{TYPE_ICONS[result.type]}</span>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <p className="text-white font-medium truncate">
                                                {result.title}
                                            </p>
                                            {result.relevance_score >= 0.8 && (
                                                <span className="badge bg-emerald-500/20 text-emerald-400 text-xs">
                                                    Relevant
                                                </span>
                                            )}
                                        </div>
                                        {result.snippet && (
                                            <p className="text-surface-300 text-sm truncate mt-1">
                                                {result.snippet}
                                            </p>
                                        )}
                                        {result.relevance_reason && (
                                            <p className="text-primary-400/70 text-xs mt-1">
                                                {result.relevance_reason}
                                            </p>
                                        )}
                                    </div>
                                </button>
                            ))}
                        </div>
                    ) : results ? (
                        <div className="px-4 py-8 text-center text-surface-400">
                            <p>No results found</p>
                            <p className="text-sm mt-1">Try different keywords</p>
                        </div>
                    ) : (
                        <div className="px-4 py-4 text-center text-surface-400 text-sm">
                            Type and press Enter to search
                        </div>
                    )}

                    {/* Search Stats */}
                    {results && (
                        <div className="px-4 py-2 border-t border-surface-700 text-xs text-surface-400 flex justify-between">
                            <span>{results.total_found} results</span>
                            <span>{results.search_time_ms}ms</span>
                        </div>
                    )}
                </div>
            )}

            {/* Backdrop to close */}
            {showResults && (
                <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowResults(false)}
                />
            )}
        </div>
    );
}
