// news-website/js/push-notifications.js

const PUBLIC_VAPID_KEY = 'BL_wQ4AU0MABrcB7uQc5dX7d725RZmGktXdlp9YD6m1MWopxpFcFMLjiBdF8pMjuAKOJmwX4a596wC0mj4HlMQ8'; // Exact wahi jo backend mein dali hai

function urlB64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function subscribeToPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications are not supported by this browser.');
        return;
    }

    try {
        // 1. Service Worker Register karein
        const registration = await navigator.serviceWorker.register('sw.js');
        console.log('Service Worker registered successfully');

        // 2. Notification Permission mangey
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            console.log('Notification permission denied.');
            return;
        }

        // 3. User ko Push Manager mein subscribe karein
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlB64ToUint8Array(PUBLIC_VAPID_KEY)
        });

        // 4. Subscription object ko JSON format me nikalein
        const subData = JSON.parse(JSON.stringify(subscription));

        // 5. Backend (Django) API par bhejein
        const token = localStorage.getItem('newsHub_accessToken'); // Optional: Agar user logged in hai
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        await fetch(`${CONFIG.API_BASE_URL}/interactions/push/subscribe/`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                endpoint: subData.endpoint,
                p256dh: subData.keys.p256dh,
                auth: subData.keys.auth
            })
        });

        console.log("Successfully subscribed to push notifications!");
        if (typeof showToast === 'function') {
            showToast("Successfully subscribed to Breaking News alerts!", "success");
        }
        
    } catch (error) {
        console.error('Error subscribing to push notifications:', error);
    }
}