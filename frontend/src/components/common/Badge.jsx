/**
 * Badge - Status/category badge component with type colors
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
        success: 'bg-success-500/20 text-success-400 border border-success-500/30',
        warning: 'bg-warning-500/20 text-warning-400 border border-warning-500/30',
        danger: 'bg-error-500/20 text-error-400 border border-error-500/30',
        info: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
        // Item type variants
        task: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
        waiting_for: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
        decision: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
        note: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
        life_admin: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    };

    const sizes = {
        xs: 'text-[10px] px-1.5 py-0.5',
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
 * Type badge - displays item type with color coding
 */
export function TypeBadge({ type, size = 'sm' }) {
    const typeLabels = {
        task: 'Task',
        waiting_for: 'Waiting For',
        decision: 'Decision',
        note: 'Note',
        life_admin: 'Life Admin'
    };

    return (
        <Badge variant={type} size={size}>
            {typeLabels[type] || type}
        </Badge>
    );
}

/**
 * Priority badge with color coding
 */
export function PriorityBadge({ priority, showLabel = true }) {
    const config = {
        high: { variant: 'danger', icon: '🔴', label: 'High' },
        medium: { variant: 'warning', icon: '🟡', label: 'Medium' },
        low: { variant: 'info', icon: '🟢', label: 'Low' }
    };

    const { variant, icon, label } = config[priority] || config.medium;

    return (
        <Badge variant={variant} size="sm">
            {icon} {showLabel && label}
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
        snoozed: { variant: 'warning', label: 'Snoozed' },
        unread: { variant: 'warning', label: 'Unread' },
        in_progress: { variant: 'primary', label: 'In Progress' },
        completed: { variant: 'success', label: 'Completed' },
        deliberating: { variant: 'warning', label: 'Deliberating' },
        decided: { variant: 'primary', label: 'Decided' },
        pending: { variant: 'warning', label: 'Pending' }
    };

    const { variant, label } = config[status] || { variant: 'default', label: status };

    return (
        <Badge variant={variant} size="sm">
            {label}
        </Badge>
    );
}

/**
 * Count badge (for notification counts, etc.)
 */
export function CountBadge({ count, variant = 'danger' }) {
    if (!count || count <= 0) return null;

    return (
        <Badge variant={variant} size="xs" className="min-w-[18px] justify-center">
            {count > 99 ? '99+' : count}
        </Badge>
    );
}
