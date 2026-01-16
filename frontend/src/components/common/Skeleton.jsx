/**
 * Skeleton - Loading placeholder components
 */

/**
 * Base skeleton with pulsing animation
 */
export function Skeleton({ className = '', width, height }) {
    return (
        <div
            className={`bg-surface-700/50 rounded-lg animate-pulse ${className}`}
            style={{ width, height }}
        />
    );
}

/**
 * Text skeleton for placeholder text lines
 */
export function SkeletonText({ lines = 1, className = '' }) {
    return (
        <div className={`space-y-2 ${className}`}>
            {Array.from({ length: lines }).map((_, i) => (
                <Skeleton
                    key={i}
                    className="h-4"
                    width={i === lines - 1 ? '70%' : '100%'}
                />
            ))}
        </div>
    );
}

/**
 * Circle skeleton for avatars/icons
 */
export function SkeletonCircle({ size = 'md', className = '' }) {
    const sizes = {
        sm: 'w-8 h-8',
        md: 'w-10 h-10',
        lg: 'w-12 h-12',
        xl: 'w-16 h-16'
    };

    return (
        <div className={`rounded-full bg-surface-700/50 animate-pulse ${sizes[size]} ${className}`} />
    );
}

/**
 * Card skeleton matching ItemCard layout
 */
export function ItemCardSkeleton() {
    return (
        <div className="bg-surface-800/60 rounded-xl border border-surface-700/50 p-4">
            <div className="flex items-start gap-3">
                <Skeleton className="w-5 h-5 rounded flex-shrink-0 mt-1" />
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                        <Skeleton className="h-5 w-16 rounded-full" />
                        <Skeleton className="h-5 w-12 rounded-full" />
                    </div>
                    <SkeletonText lines={2} />
                    <div className="flex items-center gap-3 mt-3">
                        <Skeleton className="h-4 w-20" />
                        <Skeleton className="h-4 w-16" />
                    </div>
                </div>
            </div>
        </div>
    );
}

/**
 * Bookmark card skeleton
 */
export function BookmarkCardSkeleton() {
    return (
        <div className="bg-surface-800/60 rounded-xl border border-surface-700/50 p-4">
            <div className="flex items-start gap-3">
                <Skeleton className="w-6 h-6 rounded flex-shrink-0" />
                <div className="flex-1">
                    <Skeleton className="h-5 w-3/4 mb-2" />
                    <SkeletonText lines={2} className="mb-3" />
                    <div className="flex items-center gap-2">
                        <Skeleton className="h-5 w-16 rounded-full" />
                        <Skeleton className="h-5 w-20 rounded-full" />
                        <Skeleton className="h-5 w-14 rounded-full" />
                    </div>
                </div>
            </div>
        </div>
    );
}

/**
 * Contact card skeleton
 */
export function ContactCardSkeleton() {
    return (
        <div className="bg-surface-800/60 rounded-xl border border-surface-700/50 p-4">
            <div className="flex items-center gap-3">
                <SkeletonCircle size="lg" />
                <div className="flex-1">
                    <Skeleton className="h-5 w-32 mb-2" />
                    <Skeleton className="h-4 w-24" />
                </div>
                <Skeleton className="h-8 w-20 rounded-lg" />
            </div>
        </div>
    );
}

/**
 * Stats card skeleton
 */
export function StatsCardSkeleton() {
    return (
        <div className="bg-surface-800/60 rounded-xl border border-surface-700/50 p-4">
            <div className="flex items-center justify-between">
                <div>
                    <Skeleton className="h-4 w-20 mb-2" />
                    <Skeleton className="h-8 w-12" />
                </div>
                <SkeletonCircle size="lg" />
            </div>
        </div>
    );
}

/**
 * List skeleton for generic lists
 */
export function ListSkeleton({ count = 3, CardSkeleton = ItemCardSkeleton }) {
    return (
        <div className="space-y-3">
            {Array.from({ length: count }).map((_, i) => (
                <CardSkeleton key={i} />
            ))}
        </div>
    );
}

/**
 * Chart skeleton
 */
export function ChartSkeleton({ height = 200 }) {
    return (
        <div
            className="bg-surface-800/60 rounded-xl border border-surface-700/50 p-4"
            style={{ height }}
        >
            <div className="flex items-end justify-between h-full gap-2 pb-6">
                {Array.from({ length: 7 }).map((_, i) => (
                    <Skeleton
                        key={i}
                        className="flex-1 rounded-t"
                        height={`${30 + Math.random() * 60}%`}
                    />
                ))}
            </div>
        </div>
    );
}

export default Skeleton;
