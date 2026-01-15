/**
 * LifePilot Service Worker
 * Provides offline support and caching for PWA functionality
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `lifepilot-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `lifepilot-dynamic-${CACHE_VERSION}`;
const API_CACHE = `lifepilot-api-${CACHE_VERSION}`;

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/icons/favicon.svg',
    '/icons/icon-192.png',
    '/icons/icon-512.png'
];

// API routes to cache
const API_ROUTES = [
    '/api/items',
    '/api/bookmarks',
    '/api/contacts',
    '/api/voice/settings'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('[SW] Installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
    console.log('[SW] Activating...');
    event.waitUntil(
        caches.keys()
            .then(keys => {
                return Promise.all(
                    keys
                        .filter(key => key.startsWith('lifepilot-') &&
                            key !== STATIC_CACHE &&
                            key !== DYNAMIC_CACHE &&
                            key !== API_CACHE)
                        .map(key => {
                            console.log('[SW] Deleting old cache:', key);
                            return caches.delete(key);
                        })
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - handle requests with caching strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip external requests
    if (url.origin !== location.origin) {
        return;
    }

    // API requests - Network first, fall back to cache
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request, API_CACHE));
        return;
    }

    // Static assets - Cache first, fall back to network
    if (isStaticAsset(url.pathname)) {
        event.respondWith(cacheFirst(request, STATIC_CACHE));
        return;
    }

    // HTML pages - Network first for fresh content
    if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(networkFirst(request, DYNAMIC_CACHE));
        return;
    }

    // Default - Stale while revalidate
    event.respondWith(staleWhileRevalidate(request, DYNAMIC_CACHE));
});

// Cache first strategy
async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }

    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        return offlineResponse();
    }
}

// Network first strategy
async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        return offlineResponse();
    }
}

// Stale while revalidate strategy
async function staleWhileRevalidate(request, cacheName) {
    const cached = await caches.match(request);

    const fetchPromise = fetch(request)
        .then(response => {
            if (response.ok) {
                const cache = caches.open(cacheName);
                cache.then(c => c.put(request, response.clone()));
            }
            return response;
        })
        .catch(() => null);

    return cached || fetchPromise || offlineResponse();
}

// Check if request is for a static asset
function isStaticAsset(pathname) {
    const extensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'];
    return extensions.some(ext => pathname.endsWith(ext));
}

// Offline fallback response
function offlineResponse() {
    return new Response(
        JSON.stringify({
            error: 'offline',
            message: 'You are currently offline. This content is not available.'
        }),
        {
            headers: { 'Content-Type': 'application/json' },
            status: 503
        }
    );
}

// Handle push notifications
self.addEventListener('push', event => {
    if (!event.data) return;

    const data = event.data.json();
    const options = {
        body: data.body || 'New notification from LifePilot',
        icon: '/icons/icon-192.png',
        badge: '/icons/icon-72.png',
        vibrate: [100, 50, 100],
        data: data.data || {},
        actions: data.actions || []
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'LifePilot', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();

    const urlToOpen = event.notification.data?.url || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(clientList => {
                // Focus existing window if available
                for (const client of clientList) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Open new window
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'sync-pending-actions') {
        event.waitUntil(syncPendingActions());
    }
});

async function syncPendingActions() {
    // This will be handled by the app's IndexedDB sync logic
    console.log('[SW] Background sync triggered');

    // Notify all clients that sync is available
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({ type: 'SYNC_AVAILABLE' });
    });
}

console.log('[SW] Service Worker loaded');
