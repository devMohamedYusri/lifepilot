/**
 * Button - Consistent button component with variants
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
    fullWidth = false,
    ...props
}) {
    const variants = {
        primary: `
            bg-gradient-to-r from-primary-500 to-primary-600 
            text-white font-medium
            hover:from-primary-400 hover:to-primary-500 
            shadow-lg shadow-primary-500/20
            active:scale-[0.98]
        `,
        secondary: `
            bg-surface-700/80 text-surface-100
            hover:bg-surface-600 
            border border-surface-600
            active:scale-[0.98]
        `,
        ghost: `
            bg-transparent text-surface-300
            hover:bg-white/5 hover:text-white
            active:scale-[0.98]
        `,
        danger: `
            bg-error-500/20 text-error-400 
            hover:bg-error-500/30 
            border border-error-500/30
            active:scale-[0.98]
        `,
        success: `
            bg-success-500/20 text-success-400 
            hover:bg-success-500/30 
            border border-success-500/30
            active:scale-[0.98]
        `,
        outline: `
            bg-transparent text-primary-400
            border border-primary-500/50
            hover:bg-primary-500/10 hover:border-primary-400
            active:scale-[0.98]
        `
    };

    const sizes = {
        xs: 'text-xs px-2 py-1 rounded-lg gap-1',
        sm: 'text-sm px-3 py-1.5 rounded-lg gap-1.5',
        md: 'text-sm px-4 py-2 rounded-xl gap-2',
        lg: 'text-base px-6 py-3 rounded-xl gap-2'
    };

    return (
        <button
            type={type}
            disabled={disabled || loading}
            onClick={onClick}
            className={`
                inline-flex items-center justify-center
                font-medium transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed disabled:scale-100
                focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:ring-offset-2 focus:ring-offset-surface-900
                ${variants[variant] || variants.primary}
                ${sizes[size] || sizes.md}
                ${fullWidth ? 'w-full' : ''}
                ${className}
            `}
            {...props}
        >
            {loading && (
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            )}
            {children}
        </button>
    );
}

/**
 * Icon button - For icon-only buttons with proper sizing
 */
export function IconButton({
    children,
    variant = 'ghost',
    size = 'md',
    title,
    className = '',
    ...props
}) {
    const sizes = {
        xs: 'w-6 h-6',
        sm: 'w-8 h-8',
        md: 'w-10 h-10',
        lg: 'w-12 h-12'
    };

    return (
        <Button
            variant={variant}
            className={`!p-0 !rounded-lg ${sizes[size] || sizes.md} ${className}`}
            title={title}
            aria-label={title}
            {...props}
        >
            {children}
        </Button>
    );
}

/**
 * Button group for related actions
 */
export function ButtonGroup({ children, className = '' }) {
    return (
        <div className={`inline-flex items-center gap-1 ${className}`}>
            {children}
        </div>
    );
}
