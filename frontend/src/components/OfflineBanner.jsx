/**
 * OfflineBanner - Shows offline status and pending sync count
 */
import { useOffline } from '../hooks/useOffline';

export default function OfflineBanner() {
    const { isOnline, pendingCount, isSyncing, triggerSync } = useOffline();

    // Don't show anything if online and no pending items
    if (isOnline && pendingCount === 0) {
        return null;
    }

    return (
        <div className={`
            fixed top-0 left-0 right-0 z-50 px-4 py-2 text-center text-sm
            transition-all duration-300
            ${isOnline
                ? 'bg-yellow-500/90 text-yellow-900'
                : 'bg-red-500/90 text-white'
            }
        `}>
            <div className="flex items-center justify-center gap-3">
                {!isOnline ? (
                    <>
                        <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                        <span>You're offline</span>
                        {pendingCount > 0 && (
                            <span className="px-2 py-0.5 bg-white/20 rounded-full text-xs">
                                {pendingCount} pending
                            </span>
                        )}
                    </>
                ) : (
                    <>
                        <span>Back online</span>
                        {pendingCount > 0 && (
                            <>
                                <span className="px-2 py-0.5 bg-yellow-700/30 rounded-full text-xs">
                                    {pendingCount} to sync
                                </span>
                                <button
                                    onClick={triggerSync}
                                    disabled={isSyncing}
                                    className="px-2 py-0.5 bg-yellow-700 hover:bg-yellow-800 
                                               rounded text-xs transition-colors disabled:opacity-50"
                                >
                                    {isSyncing ? 'Syncing...' : 'Sync Now'}
                                </button>
                            </>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
