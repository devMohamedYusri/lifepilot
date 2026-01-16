/**
 * EmptyState - Friendly empty state components
 */

/**
 * Generic empty state with icon, message, and action
 */
export default function EmptyState({
    icon = '📭',
    title,
    message,
    action,
    actionLabel,
    className = ''
}) {
    return (
        <div className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}>
            <div className="text-5xl mb-4">{icon}</div>
            {title && (
                <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
            )}
            {message && (
                <p className="text-surface-400 max-w-sm mb-6">{message}</p>
            )}
            {action && actionLabel && (
                <button
                    onClick={action}
                    className="px-4 py-2 bg-primary-500 hover:bg-primary-400 text-white font-medium rounded-xl transition-colors"
                >
                    {actionLabel}
                </button>
            )}
        </div>
    );
}

/**
 * Empty state for items/tasks list
 */
export function EmptyItems({ type, onAdd }) {
    const config = {
        task: {
            icon: '✅',
            title: 'No tasks yet',
            message: 'Start adding tasks to get organized. Type in the inbox above to create your first task.'
        },
        waiting_for: {
            icon: '⏳',
            title: 'Nothing waiting',
            message: 'When you delegate tasks or wait on someone, they\'ll appear here.'
        },
        decision: {
            icon: '🤔',
            title: 'No decisions pending',
            message: 'Capture decisions you\'re deliberating on to get AI-powered options.'
        },
        note: {
            icon: '📝',
            title: 'No notes yet',
            message: 'Quick thoughts and ideas will appear here when you capture them.'
        },
        life_admin: {
            icon: '🏠',
            title: 'No life admin items',
            message: 'Recurring tasks like bill payments and maintenance reminders go here.'
        },
        all: {
            icon: '📭',
            title: 'Your inbox is empty',
            message: 'Start capturing thoughts, tasks, and ideas using the input above.'
        }
    };

    const { icon, title, message } = config[type] || config.all;

    return (
        <EmptyState
            icon={icon}
            title={title}
            message={message}
            action={onAdd}
            actionLabel="Add first item"
        />
    );
}

/**
 * Empty state for bookmarks
 */
export function EmptyBookmarks({ onAdd }) {
    return (
        <EmptyState
            icon="🔖"
            title="No bookmarks saved"
            message="Save interesting articles and links here. We'll analyze them and help you build a reading queue."
            action={onAdd}
            actionLabel="Add a bookmark"
        />
    );
}

/**
 * Empty state for contacts
 */
export function EmptyContacts({ onAdd }) {
    return (
        <EmptyState
            icon="👥"
            title="No contacts yet"
            message="Start building your personal CRM. Add people you want to stay in touch with."
            action={onAdd}
            actionLabel="Add a contact"
        />
    );
}

/**
 * Empty state for decisions
 */
export function EmptyDecisions({ onAdd }) {
    return (
        <EmptyState
            icon="⚖️"
            title="No decisions to make"
            message="When you're deliberating on something, add it here to get AI-generated options and clarity."
            action={onAdd}
            actionLabel="Add a decision"
        />
    );
}

/**
 * Empty state for search results
 */
export function EmptySearch({ query }) {
    return (
        <EmptyState
            icon="🔍"
            title="No results found"
            message={query ? `No matches for "${query}". Try a different search term.` : 'Type something to search across all your data.'}
        />
    );
}

/**
 * Empty state for notifications
 */
export function EmptyNotifications() {
    return (
        <EmptyState
            icon="🔔"
            title="You're all caught up!"
            message="No new notifications. We'll let you know when something needs your attention."
        />
    );
}

/**
 * Empty state for energy logs
 */
export function EmptyEnergyLogs({ onLog }) {
    return (
        <EmptyState
            icon="⚡"
            title="No energy logs yet"
            message="Track your energy throughout the day to discover your peak performance times."
            action={onLog}
            actionLabel="Log your energy"
        />
    );
}

/**
 * Empty state for chat/conversation history
 */
export function EmptyChatHistory() {
    return (
        <EmptyState
            icon="💬"
            title="No conversations yet"
            message="Start a chat with your LifePilot assistant to get help managing your life."
        />
    );
}

/**
 * Error state component
 */
export function ErrorState({
    title = 'Something went wrong',
    message = 'An unexpected error occurred. Please try again.',
    onRetry,
    className = ''
}) {
    return (
        <div className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}>
            <div className="text-5xl mb-4">😕</div>
            <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
            <p className="text-surface-400 max-w-sm mb-6">{message}</p>
            {onRetry && (
                <button
                    onClick={onRetry}
                    className="px-4 py-2 bg-surface-700 hover:bg-surface-600 text-white font-medium rounded-xl transition-colors"
                >
                    Try again
                </button>
            )}
        </div>
    );
}
