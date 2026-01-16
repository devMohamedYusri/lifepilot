/**
 * Card - Consistent card container component
 */
export default function Card({
    children,
    className = '',
    padding = 'md',
    hover = false,
    glow = false,
    onClick
}) {
    const paddings = {
        none: '',
        sm: 'p-3',
        md: 'p-4',
        lg: 'p-6'
    };

    return (
        <div
            className={`
                bg-surface-800/60 backdrop-blur-sm
                rounded-xl border border-surface-700/50
                ${paddings[padding] || paddings.md}
                ${hover ? 'hover:bg-surface-700/60 hover:border-surface-600/50 cursor-pointer' : ''}
                ${glow ? 'shadow-glow' : ''}
                ${onClick ? 'transition-all duration-200' : ''}
                ${className}
            `}
            onClick={onClick}
            role={onClick ? 'button' : undefined}
            tabIndex={onClick ? 0 : undefined}
            onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick(e) : undefined}
        >
            {children}
        </div>
    );
}

/**
 * Card header with title and optional actions
 */
export function CardHeader({ title, subtitle, icon, actions, className = '' }) {
    return (
        <div className={`flex items-start justify-between gap-4 ${className}`}>
            <div className="flex items-start gap-3">
                {icon && (
                    <div className="w-10 h-10 rounded-lg bg-primary-500/20 flex items-center justify-center text-primary-400 flex-shrink-0">
                        {icon}
                    </div>
                )}
                <div>
                    <h3 className="font-semibold text-white">{title}</h3>
                    {subtitle && (
                        <p className="text-sm text-surface-400 mt-0.5">{subtitle}</p>
                    )}
                </div>
            </div>
            {actions && (
                <div className="flex items-center gap-2 flex-shrink-0">
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
        <div className={`mt-4 ${className}`}>
            {children}
        </div>
    );
}

/**
 * Card footer with actions
 */
export function CardFooter({ children, className = '' }) {
    return (
        <div className={`mt-4 pt-4 border-t border-surface-700/50 flex items-center gap-2 ${className}`}>
            {children}
        </div>
    );
}

/**
 * Card divider
 */
export function CardDivider() {
    return <hr className="border-surface-700/50 my-4" />;
}

/**
 * Stats card for displaying metrics
 */
export function StatsCard({ label, value, icon, trend, className = '' }) {
    return (
        <Card className={className}>
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm text-surface-400">{label}</p>
                    <p className="text-2xl font-bold text-white mt-1">{value}</p>
                    {trend && (
                        <p className={`text-xs mt-1 ${trend > 0 ? 'text-success-400' : 'text-error-400'}`}>
                            {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
                        </p>
                    )}
                </div>
                {icon && (
                    <div className="w-12 h-12 rounded-xl bg-primary-500/20 flex items-center justify-center text-primary-400">
                        {icon}
                    </div>
                )}
            </div>
        </Card>
    );
}
