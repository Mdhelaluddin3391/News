// news-website/sw.js

self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: data.icon || 'images/default-icon.png',
            data: {
                url: data.url // URL store kar rahe hain taaki click par open kar sakein
            }
        };

        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close(); // Notification click hone par close kar do

    // Jo URL humne push bheje time set kiya tha, use naye tab me open karein
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});