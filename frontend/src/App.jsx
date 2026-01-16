import { useState, useEffect } from 'react';
import { itemsApi, suggestionsApi } from './api/client';
import useItems from './hooks/useItems';
import InboxInput from './components/InboxInput';
import TodayFocus from './components/TodayFocus';
import Dashboard from './components/Dashboard';
import BookmarkManager from './components/BookmarkManager';
import DecisionReview from './components/DecisionReview';
import WeeklyReview from './components/WeeklyReview';
import ContactsManager from './components/ContactsManager';
import EnergyDashboard from './components/EnergyDashboard';
import NotificationBell from './components/NotificationBell';
import SearchBar from './components/SearchBar';
import PatternDashboard from './components/PatternDashboard';
import CalendarSettings from './components/CalendarSettings';
import { SuggestionToastContainer } from './components/SuggestionToast';
import MobileNav from './components/MobileNav';
import OfflineBanner from './components/OfflineBanner';
import FloatingAgent from './components/FloatingAgent';
import { useMobile } from './hooks/useMobile';

/**
 * LifePilot - Smart Personal Life OS
 */
import GlobalErrorBoundary from './components/common/GlobalErrorBoundary';

/**
 * LifePilot - Smart Personal Life OS
 */
export default function App() {
    return (
        <GlobalErrorBoundary>
            <AppContent />
        </GlobalErrorBoundary>
    );
}

function AppContent() {
    const {
        items,
        isLoading: itemsLoading,
        error: itemsError,
        refresh: refreshItems,
        createItem: hookCreateItem,
        updateItem: hookUpdateItem,
        deleteItem: hookDeleteItem
    } = useItems(); // Default filters

    const [loading, setLoading] = useState(true);
    const [needsFollowupIds, setNeedsFollowupIds] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    // Phase 2A: Active view tab
    const [activeView, setActiveView] = useState('tasks');

    // PWA: Mobile detection
    const { isMobile, isStandalone, isInstallable, promptInstall } = useMobile();

    useEffect(() => {
        // Initial load coordination
        Promise.all([
            refreshItems(),
            fetchFollowups(),
            fetchSuggestions()
        ]).finally(() => setLoading(false));
    }, []);

    const fetchFollowups = async () => {
        try {
            const data = await itemsApi.needsFollowup();
            setNeedsFollowupIds(data.map(item => item.id));
        } catch (err) {
            console.error('Failed to load followups', err);
        }
    };

    const fetchSuggestions = async () => {
        try {
            // Generate new suggestions then fetch pending ones
            await suggestionsApi.generate();
            const data = await suggestionsApi.list(3);
            setSuggestions(data);
        } catch (err) {
            console.log('Suggestions unavailable:', err.message);
        }
    };

    const handleItemCreated = async (newItemContent) => {
        // useItems.createItem expects content string or object? 
        // InboxInput passes string. useItems.createItem expects string.
        await hookCreateItem(newItemContent);
    };

    const handleItemUpdate = async (id, updates) => {
        await hookUpdateItem(id, updates);

        // Custom logic for followups
        if (updates.status === 'done' || updates.snoozed_until) {
            setNeedsFollowupIds(prev => prev.filter(itemId => itemId !== id));
        } else if (updates.follow_up_count !== undefined) {
            setNeedsFollowupIds(prev => prev.filter(itemId => itemId !== id));
        }
    };

    const handleItemDelete = async (id) => {
        await hookDeleteItem(id);
        setNeedsFollowupIds(prev => prev.filter(itemId => itemId !== id));
    };

    // Map mobile nav tabs to activeView values
    const handleMobileTabChange = (tabId) => {
        const tabMap = {
            'inbox': 'tasks',
            'focus': 'tasks',
            'bookmarks': 'bookmarks',
            'contacts': 'people',
            'agent': 'agent',
            'settings': 'settings'
        };
        setActiveView(tabMap[tabId] || tabId);
    };

    return (
        <div className={`min-h-screen ${isMobile ? 'pb-20' : 'pb-12'}`}>
            {/* Offline Banner */}
            <OfflineBanner />

            {/* Header with view tabs - Desktop only */}
            <header className={`border-b border-white/10 glass sticky top-0 z-40 ${isMobile ? 'py-2' : ''}`}>
                <div className="max-w-7xl mx-auto px-4">
                    {/* Top row: Logo, Search, Notification */}
                    <div className="flex items-center justify-between py-3 gap-4">
                        <div className="flex items-center gap-3 shrink-0">
                            <span className={isMobile ? 'text-2xl' : 'text-3xl'}>🚀</span>
                            <div>
                                <h1 className={`font-bold text-white ${isMobile ? 'text-lg' : 'text-xl'}`}>LifePilot</h1>
                                {!isMobile && <p className="text-xs text-surface-200/70">Smart Personal Life OS</p>}
                            </div>
                        </div>

                        {/* Search - hide on mobile */}
                        {!isMobile && <SearchBar onNavigate={(tab) => setActiveView(tab)} />}

                        <div className="flex items-center gap-4 shrink-0">
                            <NotificationBell />
                            {!isMobile && <span className="text-sm text-surface-200/60 whitespace-nowrap">
                                {new Date().toLocaleDateString('en-US', {
                                    weekday: 'long',
                                    month: 'short',
                                    day: 'numeric'
                                })}
                            </span>}
                        </div>
                    </div>

                    {/* Bottom row: Navigation Tabs - Desktop only */}
                    {!isMobile && (
                        <div className="pb-3 overflow-x-auto">
                            <div className="flex items-center gap-1.5 flex-wrap min-w-max">
                                <button
                                    onClick={() => setActiveView('tasks')}
                                    className={`px-3 py-1.5 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                                        ${activeView === 'tasks'
                                            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                            : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                                >
                                    📋 Tasks
                                </button>
                                <button
                                    onClick={() => setActiveView('bookmarks')}
                                    className={`px-3 py-1.5 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                                        ${activeView === 'bookmarks'
                                            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                            : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                                >
                                    📚 Bookmarks
                                </button>
                                <button
                                    onClick={() => setActiveView('decisions')}
                                    className={`px-3 py-1.5 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                                        ${activeView === 'decisions'
                                            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                            : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                                >
                                    🎯 Decisions
                                </button>
                                <button
                                    onClick={() => setActiveView('review')}
                                    className={`px-3 py-1.5 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                                        ${activeView === 'review'
                                            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                            : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                                >
                                    📊 Review
                                </button>
                                <button
                                    onClick={() => setActiveView('people')}
                                    className={`px-3 py-1.5 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                                        ${activeView === 'people'
                                            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                            : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                                >
                                    👥 People
                                </button>
                                <button
                                    onClick={() => setActiveView('energy')}
                                    className={`px-3 py-1.5 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                                        ${activeView === 'energy'
                                            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                            : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                                >
                                    ⚡ Energy
                                </button>
                                <button
                                    onClick={() => setActiveView('patterns')}
                                    className={`px-3 py-1.5 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                                        ${activeView === 'patterns'
                                            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                            : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                                >
                                    📊 Patterns
                                </button>

                                <button
                                    onClick={() => setActiveView('settings')}
                                    className={`px-3 py-1.5 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                                        ${activeView === 'settings'
                                            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                            : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                                >
                                    ⚙️ Settings
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </header>

            {/* Main content */}
            <main className="max-w-5xl mx-auto px-4 py-8 space-y-8">
                {activeView === 'tasks' ? (
                    <>
                        {/* Universal Inbox */}
                        <section>
                            <InboxInput onItemCreated={handleItemCreated} />
                        </section>

                        {/* Error message */}
                        {itemsError && (
                            <div className="px-4 py-3 bg-red-500/10 border border-red-500/30 
                                rounded-xl text-red-400 text-sm flex items-center gap-2">
                                <span>⚠️</span>
                                <span>{itemsError.message || 'Failed to load items'}</span>
                                <button
                                    onClick={refreshItems}
                                    className="ml-auto btn-ghost text-red-400 hover:text-red-300"
                                >
                                    Retry
                                </button>
                            </div>
                        )}

                        {/* Loading state */}
                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="flex items-center gap-3 text-primary-400">
                                    <div className="spinner"></div>
                                    <span>Loading your items...</span>
                                </div>
                            </div>
                        ) : (
                            <>
                                {/* Today's Focus */}
                                <section>
                                    <TodayFocus
                                        items={items}
                                        onItemUpdate={handleItemUpdate}
                                    />
                                </section>

                                {/* Dashboard */}
                                <section>
                                    <Dashboard
                                        items={items}
                                        onItemUpdate={handleItemUpdate}
                                        onItemDelete={handleItemDelete}
                                        needsFollowupIds={needsFollowupIds}
                                    />
                                </section>
                            </>
                        )}
                    </>
                ) : activeView === 'bookmarks' ? (
                    <BookmarkManager />
                ) : activeView === 'decisions' ? (
                    <DecisionReview />
                ) : activeView === 'review' ? (
                    <WeeklyReview />
                ) : activeView === 'people' ? (
                    <ContactsManager />
                ) : activeView === 'energy' ? (
                    <EnergyDashboard />
                ) : activeView === 'patterns' ? (
                    <PatternDashboard />
                ) : activeView === 'settings' ? (
                    <CalendarSettings />
                ) : (
                    <EnergyDashboard />
                )}
            </main>

            {/* Desktop Footer */}
            {!isMobile && (
                <footer className="fixed bottom-0 left-0 right-0 py-2 text-center 
                           text-xs text-surface-200/40 bg-surface-950/80 backdrop-blur-sm">
                    LifePilot — All data stored locally 🔒
                </footer>
            )}

            {/* Mobile Navigation */}
            {isMobile && (
                <MobileNav
                    activeTab={activeView === 'people' ? 'contacts' : activeView}
                    onTabChange={handleMobileTabChange}
                />
            )}

            {/* Suggestion Toasts */}
            <SuggestionToastContainer
                suggestions={suggestions}
                onNavigate={(view) => setActiveView(view)}
            />

            {/* Floating AI Assistant */}
            <FloatingAgent />
        </div>
    );
}


