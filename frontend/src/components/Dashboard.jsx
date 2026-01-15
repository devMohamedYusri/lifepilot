import { useState, useMemo } from 'react';
import ItemCard from './ItemCard';

/**
 * Tab configuration
 */
const TABS = [
    { id: 'all', label: 'All', icon: '📋' },
    { id: 'task', label: 'Tasks', icon: '✓' },
    { id: 'waiting_for', label: 'Waiting For', icon: '⏳' },
    { id: 'decision', label: 'Decisions', icon: '🤔' },
    { id: 'note', label: 'Notes', icon: '📝' },
    { id: 'life_admin', label: 'Life Admin', icon: '🏠' },
];

/**
 * Dashboard with tabbed view and Phase 2 follow-up indicators
 */
export default function Dashboard({ items, onItemUpdate, onItemDelete, needsFollowupIds = [] }) {
    const [activeTab, setActiveTab] = useState('all');

    const filteredItems = useMemo(() => {
        if (activeTab === 'all') return items;
        return items.filter(item => item.type === activeTab);
    }, [items, activeTab]);

    const tabCounts = useMemo(() => {
        const counts = { all: items.length };
        TABS.forEach(tab => {
            if (tab.id !== 'all') {
                counts[tab.id] = items.filter(i => i.type === tab.id).length;
            }
        });
        return counts;
    }, [items]);

    // Phase 2: Count items needing follow-up for badge
    const followUpCount = needsFollowupIds.length;

    return (
        <div className="glass rounded-2xl overflow-hidden">
            {/* Tabs */}
            <div className="border-b border-white/10 overflow-x-auto">
                <div className="flex px-2 py-2 gap-1 min-w-max">
                    {TABS.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm
                        transition-all duration-200
                        ${activeTab === tab.id
                                    ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                    : 'text-surface-200 hover:bg-white/5 hover:text-white'}`}
                        >
                            <span>{tab.icon}</span>
                            <span>{tab.label}</span>
                            {tabCounts[tab.id] > 0 && (
                                <span className={`px-1.5 py-0.5 rounded-full text-xs
                              ${activeTab === tab.id
                                        ? 'bg-primary-500/30 text-primary-300'
                                        : 'bg-surface-700 text-surface-300'}`}>
                                    {tabCounts[tab.id]}
                                </span>
                            )}
                            {/* Phase 2: Follow-up attention badge on Waiting For tab */}
                            {tab.id === 'waiting_for' && followUpCount > 0 && (
                                <span className="px-1.5 py-0.5 rounded-full text-xs bg-red-500 text-white animate-pulse">
                                    {followUpCount}
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="p-4">
                {filteredItems.length === 0 ? (
                    <div className="text-center py-12">
                        <div className="text-4xl mb-3 opacity-50">
                            {TABS.find(t => t.id === activeTab)?.icon || '📋'}
                        </div>
                        <p className="text-surface-200">
                            {activeTab === 'all'
                                ? "Your inbox is empty. Capture some thoughts above!"
                                : `No ${TABS.find(t => t.id === activeTab)?.label.toLowerCase() || 'items'} yet.`}
                        </p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {filteredItems.map(item => (
                            <ItemCard
                                key={item.id}
                                item={item}
                                onUpdate={onItemUpdate}
                                onDelete={onItemDelete}
                                needsFollowup={needsFollowupIds.includes(item.id)}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

