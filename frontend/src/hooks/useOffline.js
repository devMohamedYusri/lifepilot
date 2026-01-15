/**
 * useOffline - Hook for detecting offline state and managing pending actions
 */
import { useState, useEffect, useCallback } from 'react';

// IndexedDB for pending actions
const DB_NAME = 'lifepilot-offline';
const DB_VERSION = 1;
const PENDING_STORE = 'pending-actions';

let db = null;

// Initialize IndexedDB
function initDB() {
    return new Promise((resolve, reject) => {
        if (db) {
            resolve(db);
            return;
        }

        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };

        request.onupgradeneeded = (event) => {
            const database = event.target.result;

            if (!database.objectStoreNames.contains(PENDING_STORE)) {
                database.createObjectStore(PENDING_STORE, { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

// Add pending action to queue
async function addPendingAction(action) {
    const database = await initDB();
    return new Promise((resolve, reject) => {
        const transaction = database.transaction([PENDING_STORE], 'readwrite');
        const store = transaction.objectStore(PENDING_STORE);

        const request = store.add({
            ...action,
            timestamp: Date.now()
        });

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Get all pending actions
async function getPendingActions() {
    const database = await initDB();
    return new Promise((resolve, reject) => {
        const transaction = database.transaction([PENDING_STORE], 'readonly');
        const store = transaction.objectStore(PENDING_STORE);
        const request = store.getAll();

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Remove pending action
async function removePendingAction(id) {
    const database = await initDB();
    return new Promise((resolve, reject) => {
        const transaction = database.transaction([PENDING_STORE], 'readwrite');
        const store = transaction.objectStore(PENDING_STORE);
        const request = store.delete(id);

        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

// Clear all pending actions
async function clearPendingActions() {
    const database = await initDB();
    return new Promise((resolve, reject) => {
        const transaction = database.transaction([PENDING_STORE], 'readwrite');
        const store = transaction.objectStore(PENDING_STORE);
        const request = store.clear();

        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

export function useOffline() {
    const [isOnline, setIsOnline] = useState(navigator.onLine);
    const [pendingCount, setPendingCount] = useState(0);
    const [isSyncing, setIsSyncing] = useState(false);

    // Update pending count
    const refreshPendingCount = useCallback(async () => {
        try {
            const actions = await getPendingActions();
            setPendingCount(actions.length);
        } catch (error) {
            console.error('Failed to get pending actions:', error);
        }
    }, []);

    // Handle online/offline events
    useEffect(() => {
        const handleOnline = () => {
            setIsOnline(true);
            // Trigger sync when coming back online
            syncPendingActions();
        };

        const handleOffline = () => {
            setIsOnline(false);
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        // Listen for service worker sync messages
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                if (event.data?.type === 'SYNC_AVAILABLE') {
                    syncPendingActions();
                }
            });
        }

        // Initial pending count
        refreshPendingCount();

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, [refreshPendingCount]);

    // Queue action for later sync
    const queueAction = useCallback(async (type, endpoint, method, data) => {
        try {
            await addPendingAction({ type, endpoint, method, data });
            await refreshPendingCount();
            return true;
        } catch (error) {
            console.error('Failed to queue action:', error);
            return false;
        }
    }, [refreshPendingCount]);

    // Sync all pending actions
    const syncPendingActions = useCallback(async () => {
        if (!navigator.onLine || isSyncing) return;

        setIsSyncing(true);

        try {
            const actions = await getPendingActions();

            for (const action of actions) {
                try {
                    const response = await fetch(action.endpoint, {
                        method: action.method,
                        headers: { 'Content-Type': 'application/json' },
                        body: action.data ? JSON.stringify(action.data) : undefined
                    });

                    if (response.ok) {
                        await removePendingAction(action.id);
                    }
                } catch (error) {
                    console.error('Failed to sync action:', action, error);
                    // Keep in queue for retry
                }
            }

            await refreshPendingCount();
        } finally {
            setIsSyncing(false);
        }
    }, [isSyncing, refreshPendingCount]);

    // Manual sync trigger
    const triggerSync = useCallback(async () => {
        if (navigator.onLine) {
            await syncPendingActions();
        }
    }, [syncPendingActions]);

    return {
        isOnline,
        pendingCount,
        isSyncing,
        queueAction,
        triggerSync,
        refreshPendingCount
    };
}

export default useOffline;
