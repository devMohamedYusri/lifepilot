import { useState, useEffect, useCallback } from 'react';
import { notificationsApi } from '../api/client';

/**
 * NotificationBell - Header notification icon with dropdown panel
 */
export default function NotificationBell() {
    const [count, setCount] = useState(0);
    const [highPriority, setHighPriority] = useState(0);
    const [notifications, setNotifications] = useState([]);
    const [showPanel, setShowPanel] = useState(false);
    const [loading, setLoading] = useState(false);

    // Fetch notification count
    const fetchCount = useCallback(async () => {
        try {
            const data = await notificationsApi.count();
            setCount(data.total || 0);
            setHighPriority(data.high_priority || 0);
        } catch (err) {
            console.error('Failed to fetch notification count:', err);
        }
    }, []);

    // Fetch full notifications
    const fetchNotifications = async () => {
        setLoading(true);
        try {
            const data = await notificationsApi.pending();
            setNotifications(data || []);
        } catch (err) {
            console.error('Failed to fetch notifications:', err);
        } finally {
            setLoading(false);
        }
    };

    // Generate notifications
    const generateNotifications = async () => {
        try {
            await notificationsApi.generate();
            fetchNotifications();
            fetchCount();
        } catch (err) {
            console.error('Failed to generate notifications:', err);
        }
    };

    // Dismiss notification
    const handleDismiss = async (id) => {
        try {
            await notificationsApi.dismiss(id);
            setNotifications(prev => prev.filter(n => n.id !== id));
            setCount(prev => Math.max(0, prev - 1));
        } catch (err) {
            console.error('Failed to dismiss notification:', err);
        }
    };

    // Act on notification
    const handleAct = async (notification) => {
        try {
            const result = await notificationsApi.act(notification.id);
            setNotifications(prev => prev.filter(n => n.id !== notification.id));
            setCount(prev => Math.max(0, prev - 1));
            setShowPanel(false);

            // Navigate based on linked_type
            // This could trigger a callback or use a router
            console.log('Navigate to:', result.linked_type, result.linked_id);
        } catch (err) {
            console.error('Failed to act on notification:', err);
        }
    };

    // Clear all
    const handleClearAll = async () => {
        try {
            await notificationsApi.clearAll();
            setNotifications([]);
            setCount(0);
        } catch (err) {
            console.error('Failed to clear notifications:', err);
        }
    };

    // Poll for count every 5 minutes
    useEffect(() => {
        fetchCount();
        generateNotifications(); // Generate on mount

        const interval = setInterval(fetchCount, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, [fetchCount]);

    // Fetch full list when panel opens
    useEffect(() => {
        if (showPanel) {
            fetchNotifications();
        }
    }, [showPanel]);

    const typeIcon = {
        task_due: '📋',
        follow_up: '📞',
        contact: '👥',
        birthday: '🎂',
        review: '📊',
        energy_check: '⚡',
        reading: '📚',
        decision: '🎯',
        insight: '💡',
        custom: '🔔'
    };

    const priorityColor = {
        high: 'border-l-red-400',
        medium: 'border-l-amber-400',
        low: 'border-l-blue-400'
    };

    return (
        <div className="relative">
            {/* Bell Icon */}
            <button
                onClick={() => setShowPanel(!showPanel)}
                className="relative p-2 rounded-lg hover:bg-white/10 transition-all"
            >
                <span className="text-xl">🔔</span>
                {count > 0 && (
                    <span className={`absolute -top-1 -right-1 min-w-[20px] h-5 flex items-center justify-center 
                        text-xs font-bold rounded-full px-1
                        ${highPriority > 0 ? 'bg-red-500 text-white animate-pulse' : 'bg-primary-500 text-white'}`}>
                        {count > 99 ? '99+' : count}
                    </span>
                )}
            </button>

            {/* Dropdown Panel */}
            {showPanel && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-40"
                        onClick={() => setShowPanel(false)}
                    />

                    {/* Panel */}
                    <div className="absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto 
                                    glass rounded-xl shadow-2xl z-50 border border-surface-600">
                        {/* Header */}
                        <div className="flex items-center justify-between p-4 border-b border-surface-700">
                            <h3 className="text-white font-semibold">Notifications</h3>
                            <div className="flex gap-2">
                                <button
                                    onClick={generateNotifications}
                                    className="text-surface-400 hover:text-white text-sm"
                                    title="Refresh"
                                >
                                    🔄
                                </button>
                                {notifications.length > 0 && (
                                    <button
                                        onClick={handleClearAll}
                                        className="text-surface-400 hover:text-white text-sm"
                                    >
                                        Clear all
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Content */}
                        <div className="divide-y divide-surface-700">
                            {loading ? (
                                <div className="p-6 text-center text-surface-400">
                                    Loading...
                                </div>
                            ) : notifications.length === 0 ? (
                                <div className="p-6 text-center">
                                    <div className="text-4xl mb-2">🎉</div>
                                    <p className="text-surface-300">All caught up!</p>
                                    <p className="text-surface-500 text-sm mt-1">No pending notifications</p>
                                </div>
                            ) : (
                                notifications.map(notification => (
                                    <div
                                        key={notification.id}
                                        className={`p-3 hover:bg-white/5 cursor-pointer border-l-4 ${priorityColor[notification.priority] || 'border-l-surface-500'}`}
                                    >
                                        <div className="flex items-start gap-3">
                                            <span className="text-xl">{typeIcon[notification.type] || '🔔'}</span>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-white font-medium text-sm truncate">
                                                    {notification.title}
                                                </div>
                                                {notification.message && (
                                                    <p className="text-surface-400 text-xs mt-0.5 line-clamp-2">
                                                        {notification.message}
                                                    </p>
                                                )}
                                            </div>
                                            <div className="flex gap-1">
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleAct(notification); }}
                                                    className="p-1 hover:bg-white/10 rounded text-xs text-primary-400"
                                                    title="Go to item"
                                                >
                                                    →
                                                </button>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleDismiss(notification.id); }}
                                                    className="p-1 hover:bg-white/10 rounded text-xs text-surface-400"
                                                    title="Dismiss"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
