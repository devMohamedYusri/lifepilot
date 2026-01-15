/**
 * Button - Consistent button component
 */
export default function Button({
    children,
    variant = 'primary',
    size = 'md',
    disabled = false,
    loading = false,
    onClick,
    type = 'button',
    className = '',
    ...props
}) {
    const variants = {
        primary: 'bg-gradient-to-r from-primary-500 to-accent-500 text-white hover:opacity-90 shadow-lg shadow-primary-500/20',
        secondary: 'bg-surface-700 text-surface-200 hover:bg-surface-600 border border-white/10',
        ghost: 'bg-transparent text-surface-200 hover:bg-white/5 hover:text-white',
        danger: 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30',
        success: 'bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/30'
    };

    const sizes = {
        sm: 'text-xs px-2 py-1 rounded-lg',
        md: 'text-sm px-4 py-2 rounded-xl',
        lg: 'text-base px-6 py-3 rounded-xl'
    };

    return (
        <button
            type={type}
            disabled={disabled || loading}
            onClick={onClick}
            className={`
                inline-flex items-center justify-center gap-2 
                font-medium transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
                ${variants[variant] || variants.primary}
                ${sizes[size] || sizes.md}
                ${className}
            `}
            {...props}
        >
            {loading && (
                <div className="spinner w-4 h-4" />
            )}
            {children}
        </button>
    );
}

/**
 * Icon button - For icon-only buttons
 */
export function IconButton({
    children,
    variant = 'ghost',
    size = 'md',
    title,
    ...props
}) {
    const sizes = {
        sm: 'w-6 h-6',
        md: 'w-8 h-8',
        lg: 'w-10 h-10'
    };

    return (
        <Button
            variant={variant}
            className={`!p-0 ${sizes[size] || sizes.md}`}
            title={title}
            aria-label={title}
            {...props}
        >
            {children}
        </Button>
    );
}
