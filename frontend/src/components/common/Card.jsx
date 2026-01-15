/**
 * Card - Consistent card container component
 */
export default function Card({
    children,
    className = '',
    padding = true,
    hover = false,
    onClick
}) {
    return (
        <div
            className={`
                glass rounded-xl border border-white/10
                ${padding ? 'p-4' : ''}
                ${hover ? 'hover:bg-white/5 cursor-pointer transition-colors' : ''}
                ${className}
            `}
            onClick={onClick}
            role={onClick ? 'button' : undefined}
            tabIndex={onClick ? 0 : undefined}
        >
            {children}
        </div>
    );
}

/**
 * Card header with title and optional actions
 */
export function CardHeader({ title, subtitle, actions, className = '' }) {
    return (
        <div className={`flex items-start justify-between gap-4 ${className}`}>
            <div>
                <h3 className="font-semibold text-white">{title}</h3>
                {subtitle && (
                    <p className="text-sm text-surface-200/70 mt-0.5">{subtitle}</p>
                )}
            </div>
            {actions && (
                <div className="flex items-center gap-2">
                    {actions}
                </div>
            )}
        </div>
    );
}

/**
 * Card content section
 */
export function CardContent({ children, className = '' }) {
    return (
        <div className={`mt-3 ${className}`}>
            {children}
        </div>
    );
}

/**
 * Card footer with actions
 */
export function CardFooter({ children, className = '' }) {
    return (
        <div className={`mt-4 pt-3 border-t border-white/10 flex items-center gap-2 ${className}`}>
            {children}
        </div>
    );
}
