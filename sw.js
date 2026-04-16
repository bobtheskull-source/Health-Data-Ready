const CACHE_NAME = 'hdr-cache-v5';
const STATIC_ASSETS = [
  '/Health-Data-Ready/',
  '/Health-Data-Ready/index.html',
  '/Health-Data-Ready/auth.html',
  '/Health-Data-Ready/onboarding.html',
  '/Health-Data-Ready/dashboard.html',
  '/Health-Data-Ready/engagement.html',
  '/Health-Data-Ready/workspace.html',
  '/Health-Data-Ready/doc-device-inventory.html',
  '/Health-Data-Ready/doc-vulnerability.html',
  '/Health-Data-Ready/doc-mhmd-compliance.html',
  '/Health-Data-Ready/doc-remediation.html',
  '/Health-Data-Ready/row-table-styles.css',
  '/Health-Data-Ready/data-model.js',
  '/Health-Data-Ready/row-table-engine.js'
];
// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Fetch: serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      // Return cached or fetch from network
      return response || fetch(event.request).then((fetchResponse) => {
        // Cache successful API responses for offline
        if (event.request.url.includes('/api/') && fetchResponse.ok) {
          const responseClone = fetchResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return fetchResponse;
      });
    }).catch(() => {
      // Offline fallback
      if (event.request.mode === 'navigate') {
        return caches.match('/Health-Data-Ready/index.html');
      }
    })
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncData());
  }
});

async function syncData() {
  // Replay queued API calls when back online
  const queue = await getQueuedRequests();
  for (const request of queue) {
    try {
      await fetch(request.url, {
        method: request.method,
        headers: request.headers,
        body: request.body
      });
      await removeFromQueue(request.id);
    } catch (error) {
      console.error('Sync failed for request:', request.id);
    }
  }
}

// Placeholder functions (implement with IndexedDB in production)
async function getQueuedRequests() {
  return [];
}

async function removeFromQueue(id) {
  // Remove from IndexedDB
}
