/**
 * MobileNav - Bottom navigation bar for mobile devices
 */
import { memo } from 'react';

const NAV_ITEMS = [
    { id: 'inbox', label: 'Inbox', icon: '📥', emoji: true },
    { id: 'focus', label: 'Focus', icon: '🎯', emoji: true },
    { id: 'bookmarks', label: 'Saved', icon: '🔖', emoji: true },
    { id: 'contacts', label: 'People', icon: '👥', emoji: true },
    { id: 'settings', label: 'Settings', icon: '⚙️', emoji: true }
];

function MobileNav({ activeTab, onTabChange }) {
    return (
        <nav className="fixed bottom-0 left-0 right-0 z-40 bg-surface-900/95 backdrop-blur-lg 
                        border-t border-surface-700 safe-area-bottom">
            <div className="flex items-center justify-around h-16">
                {NAV_ITEMS.map(item => (
                    <button
                        key={item.id}
                        onClick={() => onTabChange(item.id)}
                        className={`
                            flex flex-col items-center justify-center
                            w-full h-full gap-0.5 transition-colors
                            ${activeTab === item.id
                                ? 'text-primary-400'
                                : 'text-surface-400 active:text-surface-200'
                            }
                        `}
                    >
                        <span className="text-xl">{item.icon}</span>
                        <span className="text-xs font-medium">{item.label}</span>
                        {activeTab === item.id && (
                            <span className="absolute bottom-1 w-8 h-0.5 bg-primary-400 rounded-full" />
                        )}
                    </button>
                ))}
            </div>
        </nav>
    );
}

export default memo(MobileNav);
