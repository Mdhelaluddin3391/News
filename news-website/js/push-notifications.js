const PUBLIC_VAPID_KEY = CONFIG.VAPID_PUBLIC_KEY;
let siteServiceWorkerRegistration = null;

function reportPushError(error, context = {}) {
    if (typeof window.reportFrontendError === 'function') {
        window.reportFrontendError(error, { scope: 'push', ...context });
    }
}

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

async function registerSiteServiceWorker() {
    if (!('serviceWorker' in navigator)) {
        return null;
    }

    if (!siteServiceWorkerRegistration) {
        siteServiceWorkerRegistration = await navigator.serviceWorker.register('sw.js');
    }

    return siteServiceWorkerRegistration;
}

document.addEventListener('DOMContentLoaded', () => {
    registerSiteServiceWorker().catch((error) => {
        reportPushError(error, { action: 'registerServiceWorker' });
        console.error('Service worker registration failed:', error);
    });
});

async function subscribeToPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications are not supported by this browser.');
        return;
    }

    try {
        const registration = await registerSiteServiceWorker();
        if (!registration) {
            throw new Error('Service worker registration is not available.');
        }

        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            console.log('Notification permission denied.');
            return;
        }

        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlB64ToUint8Array(PUBLIC_VAPID_KEY)
        });

        const subData = JSON.parse(JSON.stringify(subscription));

        await apiFetch(`${CONFIG.API_BASE_URL}/interactions/push/subscribe/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
        reportPushError(error, { action: 'subscribeToPush' });
        console.error('Error subscribing to push notifications:', error);
    }
}
