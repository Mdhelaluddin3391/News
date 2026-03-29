const CACHE_VERSION = 'v5';
const SHELL_CACHE = `forex-times-shell-${CACHE_VERSION}`;
const PAGE_CACHE = `forex-times-pages-${CACHE_VERSION}`;
const ASSET_CACHE = `forex-times-assets-${CACHE_VERSION}`;
const API_CACHE = `forex-times-api-${CACHE_VERSION}`;
const OFFLINE_FALLBACK_URL = '/index.html';
const PRECACHE_URLS = [
    '/',
    '/index.html',
    '/404.html',
    '/about.html',
    '/advertise.html',
    '/article.html',
    '/author.html',
    '/authors.html',
    '/careers.html',
    '/contact.html',
    '/edit-profile.html',
    '/faq.html',
    '/forgot-password.html',
    '/login.html',
    '/privacy.html',
    '/profile.html',
    '/register.html',
    '/reset-password.html',
    '/saved.html',
    '/search.html',
    '/tag.html',
    '/terms.html',
    '/unsubscribe.html',
    '/verify-email.html',
    '/manifest.json',
    '/robots.txt',
    '/components/header.html',
    '/components/footer.html',
    '/css/article.css',
    '/css/auth.css',
    '/css/author.css',
    '/css/authors.css',
    '/css/comments.css',
    '/css/edit-profile.css',
    '/css/extra-pages.css',
    '/css/faq.css',
    '/css/pages.css',
    '/css/search.css',
    '/css/style.css',
    '/js/ad-manager.js',
    '/js/advertise.js',
    '/js/article.js',
    '/js/auth.js',
    '/js/author.js',
    '/js/authors.js',
    '/js/careers.js',
    '/js/comments.js',
    '/js/config.js',
    '/js/contact.js',
    '/js/edit-profile.js',
    '/js/faq.js',
    '/js/forgot-password.js',
    '/js/homepage.js',
    '/js/index-ui.js',
    '/js/loadComponents.js',
    '/js/login.js',
    '/js/poll.js',
    '/js/profile.js',
    '/js/push-notifications.js',
    '/js/register.js',
    '/js/related.js',
    '/js/reset-password.js',
    '/js/saved.js',
    '/js/script.js',
    '/js/search.js',
    '/js/tag.js',
    '/js/unsubscribe.js',
    '/js/verify-email.js',
    '/images/default-avatar.png',
    '/images/default-news.png'
];
const MANAGED_CACHES = [SHELL_CACHE, PAGE_CACHE, ASSET_CACHE, API_CACHE];

self.addEventListener('install', (event) => {
    event.waitUntil((async () => {
        const cache = await caches.open(SHELL_CACHE);
        await cache.addAll(PRECACHE_URLS);
        await self.skipWaiting();
    })());
});

self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
        const keys = await caches.keys();
        await Promise.all(
            keys
                .filter((key) => !MANAGED_CACHES.includes(key))
                .map((key) => caches.delete(key))
        );

        if ('navigationPreload' in self.registration) {
            await self.registration.navigationPreload.enable();
        }

        await self.clients.claim();
    })());
});

function isApiRequest(url) {
    return url.origin === self.location.origin && url.pathname.startsWith('/api/');
}

function isPageRequest(request) {
    return request.mode === 'navigate' || request.destination === 'document';
}

function isStaticAssetRequest(request, url) {
    return (
        url.origin === self.location.origin &&
        ['style', 'script', 'image', 'font'].includes(request.destination)
    );
}

async function putInCache(cacheName, request, response) {
    if (!response || !response.ok || response.type === 'error') {
        return response;
    }

    const cache = await caches.open(cacheName);
    await cache.put(request, response.clone());
    return response;
}

async function networkFirst(request, cacheName, fallbackUrl, preloadResponsePromise) {
    const cache = await caches.open(cacheName);

    try {
        const preloadResponse = preloadResponsePromise ? await preloadResponsePromise : null;
        if (preloadResponse) {
            await cache.put(request, preloadResponse.clone());
            return preloadResponse;
        }

        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            await cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (_error) {
        const cachedResponse = await cache.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        if (fallbackUrl) {
            const fallbackResponse = await caches.match(fallbackUrl);
            if (fallbackResponse) {
                return fallbackResponse;
            }
        }

        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: {
                'Content-Type': 'text/plain; charset=utf-8'
            }
        });
    }
}

async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);

    const networkPromise = fetch(request)
        .then((response) => putInCache(cacheName, request, response))
        .catch(() => cachedResponse);

    return cachedResponse || networkPromise;
}

self.addEventListener('fetch', (event) => {
    const { request } = event;

    if (request.method !== 'GET') {
        return;
    }

    const url = new URL(request.url);
    if (!['http:', 'https:'].includes(url.protocol)) {
        return;
    }

    if (isPageRequest(request)) {
        event.respondWith(networkFirst(
            request,
            PAGE_CACHE,
            OFFLINE_FALLBACK_URL,
            event.preloadResponse
        ));
        return;
    }

    if (isApiRequest(url)) {
        event.respondWith(networkFirst(request, API_CACHE));
        return;
    }

    if (isStaticAssetRequest(request, url) || url.origin === self.location.origin) {
        event.respondWith(staleWhileRevalidate(request, ASSET_CACHE));
    }
});

self.addEventListener('push', (event) => {
    if (!event.data) {
        return;
    }

    let data = {};
    try {
        data = event.data.json();
    } catch (_error) {
        data = { title: 'Forex Times', body: event.data.text() };
    }

    const options = {
        body: data.body || 'Breaking news is available.',
        icon: data.icon || '/images/default-news.png',
        badge: data.badge || '/images/default-avatar.png',
        vibrate: [200, 100, 200, 100, 200, 100, 200],
        requireInteraction: true,
        data: {
            url: data.url || '/'
        },
        actions: [
            { action: 'open_url', title: 'Read Now' }
        ]
    };

    event.waitUntil(self.registration.showNotification(data.title || 'Forex Times', options));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const urlToOpen = new URL(event.notification.data?.url || '/', self.location.origin).href;

    event.waitUntil((async () => {
        const windowClients = await clients.matchAll({ type: 'window', includeUncontrolled: true });
        for (const client of windowClients) {
            if (client.url === urlToOpen && 'focus' in client) {
                return client.focus();
            }
        }

        if (clients.openWindow) {
            return clients.openWindow(urlToOpen);
        }
    })());
});
