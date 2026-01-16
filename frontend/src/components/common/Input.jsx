/**
 * Input - Consistent input component
 */
export default function Input({
    type = 'text',
    value,
    onChange,
    placeholder,
    disabled = false,
    error = null,
    className = '',
    leftIcon = null,
    rightIcon = null,
    ...props
}) {
    return (
        <div className="relative">
            {leftIcon && (
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">
                    {leftIcon}
                </div>
            )}
            <input
                type={type}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                disabled={disabled}
                className={`
                    w-full px-4 py-3 
                    bg-surface-800/50 
                    border ${error ? 'border-error-500' : 'border-surface-700'}
                    rounded-xl 
                    text-white placeholder-surface-400
                    focus:outline-none focus:ring-2 
                    ${error ? 'focus:ring-error-500/50 focus:border-error-500' : 'focus:ring-primary-500/50 focus:border-primary-500'}
                    transition-all duration-200
                    disabled:opacity-50 disabled:cursor-not-allowed
                    ${leftIcon ? 'pl-10' : ''}
                    ${rightIcon ? 'pr-10' : ''}
                    ${className}
                `}
                {...props}
            />
            {rightIcon && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400">
                    {rightIcon}
                </div>
            )}
            {error && (
                <p className="mt-1 text-xs text-error-400">{error}</p>
            )}
        </div>
    );
}

/**
 * Textarea - Multi-line input
 */
export function Textarea({
    value,
    onChange,
    placeholder,
    rows = 3,
    disabled = false,
    error = null,
    className = '',
    ...props
}) {
    return (
        <div>
            <textarea
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                rows={rows}
                disabled={disabled}
                className={`
                    w-full px-4 py-3 
                    bg-surface-800/50 
                    border ${error ? 'border-error-500' : 'border-surface-700'}
                    rounded-xl 
                    text-white placeholder-surface-400
                    focus:outline-none focus:ring-2 
                    ${error ? 'focus:ring-error-500/50' : 'focus:ring-primary-500/50 focus:border-primary-500'}
                    transition-all duration-200
                    disabled:opacity-50 disabled:cursor-not-allowed
                    resize-none
                    ${className}
                `}
                {...props}
            />
            {error && (
                <p className="mt-1 text-xs text-error-400">{error}</p>
            )}
        </div>
    );
}

/**
 * Select - Dropdown select
 */
export function Select({
    value,
    onChange,
    options = [],
    placeholder = 'Select...',
    disabled = false,
    className = '',
    ...props
}) {
    return (
        <select
            value={value}
            onChange={onChange}
            disabled={disabled}
            className={`
                w-full px-4 py-3 
                bg-surface-800/50 
                border border-surface-700
                rounded-xl 
                text-white
                focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500
                transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
                appearance-none
                cursor-pointer
                ${className}
            `}
            style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 12px center',
                backgroundSize: '20px'
            }}
            {...props}
        >
            {placeholder && (
                <option value="" disabled>{placeholder}</option>
            )}
            {options.map(opt => (
                <option key={opt.value} value={opt.value}>
                    {opt.label}
                </option>
            ))}
        </select>
    );
}

/**
 * FormGroup - Label and input wrapper
 */
export function FormGroup({ label, required = false, children, className = '' }) {
    return (
        <div className={className}>
            {label && (
                <label className="block text-sm font-medium text-surface-300 mb-2">
                    {label}
                    {required && <span className="text-error-400 ml-1">*</span>}
                </label>
            )}
            {children}
        </div>
    );
}
