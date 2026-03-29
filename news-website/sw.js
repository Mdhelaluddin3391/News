const STATIC_CACHE = 'forex-times-static-v4';
const API_CACHE = 'forex-times-api-v2';
const CORE_ASSETS = [
    './',
    './index.html',
    './article.html',
    './search.html',
    './login.html',
    './register.html',
    './profile.html',
    './saved.html',
    './components/header.html',
    './components/footer.html',
    './css/style.css',
    './css/article.css',
    './css/auth.css',
    './css/search.css',
    './css/comments.css',
    './js/config.js',
    './js/auth.js',
    './js/script.js',
    './js/homepage.js',
    './js/index-ui.js',
    './js/loadComponents.js',
    './js/search.js',
    './js/article.js',
    './js/comments.js',
    './js/push-notifications.js',
    './images/default-news.png',
    './images/default-avatar.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => cache.addAll(CORE_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys
                .filter((key) => ![STATIC_CACHE, API_CACHE].includes(key))
                .map((key) => caches.delete(key))
        )).then(() => self.clients.claim())
    );
});

function isApiRequest(url) {
    return url.pathname.includes('/api/');
}

function isStaticAssetRequest(request) {
    return ['style', 'script', 'image', 'font'].includes(request.destination);
}

async function networkFirst(request, cacheName, fallbackUrl) {
    const cache = await caches.open(cacheName);

    try {
        const freshResponse = await fetch(request);
        if (freshResponse && freshResponse.ok) {
            cache.put(request, freshResponse.clone());
        }
        return freshResponse;
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

        throw _error;
    }
}

async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);

    const networkFetch = fetch(request).then((response) => {
        if (response && response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    }).catch(() => cachedResponse);

    return cachedResponse || networkFetch;
}

self.addEventListener('fetch', (event) => {
    const { request } = event;

    if (request.method !== 'GET') {
        return;
    }

    const url = new URL(request.url);

    if (request.mode === 'navigate') {
        event.respondWith(networkFirst(request, STATIC_CACHE, './index.html'));
        return;
    }

    if (isApiRequest(url)) {
        event.respondWith(networkFirst(request, API_CACHE));
        return;
    }

    if (isStaticAssetRequest(request) || url.origin === self.location.origin) {
        event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
    }
});

self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();

        const options = {
            body: data.body,
            icon: data.icon || '',
            badge: '',
            vibrate: [200, 100, 200, 100, 200, 100, 200],
            requireInteraction: true,
            data: {
                url: data.url || '/'
            },
            actions: [
                { action: 'open_url', title: 'Read Now' }
            ]
        };

        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const urlToOpen = event.notification.data.url;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(windowClients) {
            for (let i = 0; i < windowClients.length; i++) {
                const client = windowClients[i];
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }

            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});
