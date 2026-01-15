/**
 * Badge - Status/category badge component
 */
export default function Badge({
    children,
    variant = 'default',
    size = 'md',
    className = ''
}) {
    const variants = {
        default: 'bg-surface-700 text-surface-200',
        primary: 'bg-primary-500/20 text-primary-400 border border-primary-500/30',
        success: 'bg-green-500/20 text-green-400 border border-green-500/30',
        warning: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
        danger: 'bg-red-500/20 text-red-400 border border-red-500/30',
        info: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    };

    const sizes = {
        sm: 'text-xs px-1.5 py-0.5',
        md: 'text-xs px-2 py-1',
        lg: 'text-sm px-3 py-1'
    };

    return (
        <span
            className={`
                inline-flex items-center rounded-full font-medium
                ${variants[variant] || variants.default}
                ${sizes[size] || sizes.md}
                ${className}
            `}
        >
            {children}
        </span>
    );
}

/**
 * Priority badge with color coding
 */
export function PriorityBadge({ priority }) {
    const config = {
        high: { variant: 'danger', emoji: '🔴' },
        medium: { variant: 'warning', emoji: '🟡' },
        low: { variant: 'info', emoji: '🟢' }
    };

    const { variant, emoji } = config[priority] || config.medium;

    return (
        <Badge variant={variant} size="sm">
            {emoji} {priority}
        </Badge>
    );
}

/**
 * Status badge with color coding
 */
export function StatusBadge({ status }) {
    const config = {
        active: { variant: 'primary', label: 'Active' },
        done: { variant: 'success', label: 'Done' },
        inbox: { variant: 'default', label: 'Inbox' },
        archived: { variant: 'default', label: 'Archived' },
        unread: { variant: 'warning', label: 'Unread' },
        in_progress: { variant: 'primary', label: 'In Progress' },
        completed: { variant: 'success', label: 'Completed' },
        deliberating: { variant: 'warning', label: 'Deliberating' },
        decided: { variant: 'primary', label: 'Decided' }
    };

    const { variant, label } = config[status] || { variant: 'default', label: status };

    return (
        <Badge variant={variant} size="sm">
            {label}
        </Badge>
    );
}
