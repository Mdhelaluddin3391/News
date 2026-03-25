// news-website/sw.js
self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        
        const options = {
            body: data.body,
            icon: data.icon || '',
            badge: '', // Android status bar icon
            vibrate: [200, 100, 200, 100, 200, 100, 200], // Phone ko vibrate karne ke liye
            requireInteraction: true, // Notification tab tak screen par rahegi jab tak user click/dismiss na kare
            data: {
                url: data.url || '/'
            },
            actions: [
                { action: 'open_url', title: 'Read Now' } // Notification par ek button aayega
            ]
        };

        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close(); // Click hote hi notification band ho jayegi

    // Jis URL ka data bheja tha, usko background se uthakar browser me open karega
    const urlToOpen = event.notification.data.url;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(windowClients) {
            // Agar koi tab pehle se khuli hai toh usme focus karo
            for (let i = 0; i < windowClients.length; i++) {
                const client = windowClients[i];
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            // Agar tab band hai toh nayi window open karo
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});