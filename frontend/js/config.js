const APP_CONFIG = window.__APP_CONFIG__ || {};
const isFileProtocol = window.location.protocol === 'file:';

// Single source-of-truth: global API base URL
// Dynamically set based on environment
if (typeof API_BASE_URL === 'undefined') {
    const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || isFileProtocol;
    window.API_BASE_URL = isDevelopment 
        ? 'http://localhost:8000/api'
        : `${window.location.protocol}//${window.location.hostname}${window.location.port ? ':' + window.location.port : ''}/api`;
}

const CONFIG = {
    API_BASE_URL: APP_CONFIG.API_BASE_URL || window.API_BASE_URL,
    GOOGLE_CLIENT_ID: APP_CONFIG.GOOGLE_CLIENT_ID || '615098838513-hnphi7ekcv9nhjv94f0mfj0509nd63hu.apps.googleusercontent.com',
    VAPID_PUBLIC_KEY: APP_CONFIG.VAPID_PUBLIC_KEY || 'BL_wQ4AU0MABrcB7uQc5dX7d725RZmGktXdlp9YD6m1MWopxpFcFMLjiBdF8pMjuAKOJmwX4a596wC0mj4HlMQ8',
    SENTRY_DSN: APP_CONFIG.SENTRY_DSN || '',
    SENTRY_ENVIRONMENT: APP_CONFIG.SENTRY_ENVIRONMENT || (window.location.hostname === 'localhost' || isFileProtocol ? 'development' : 'production'),
    SENTRY_RELEASE: APP_CONFIG.SENTRY_RELEASE || '',
    SENTRY_TRACES_SAMPLE_RATE: Number(APP_CONFIG.SENTRY_TRACES_SAMPLE_RATE || 0)
};

// Expose for maximum compatibility
window.APP_CONFIG = Object.freeze({
    ...CONFIG,
    ...window.APP_CONFIG,
});
window.CONFIG = window.APP_CONFIG;

function apiFetch(endpoint, options = {}) {
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${window.APP_CONFIG.API_BASE_URL}${normalizedEndpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        credentials: 'include',
        ...options,
    };

    return fetch(url, defaultOptions).then(async (response) => {
        if (!response.ok) {
            const text = await response.text();
            const message = `API error ${response.status}: ${text}`;
            const err = new Error(message);
            err.response = response;
            throw err;
        }
        return response.json();
    });
}

window.apiFetch = apiFetch;

window.reportFrontendError = function reportFrontendError(error, context = {}) {
    if (!window.Sentry) {
        return;
    }

    if (error instanceof Error) {
        const tags = context.scope ? { scope: context.scope } : undefined;
        window.Sentry.captureException(error, { tags, extra: context });
        return;
    }

    window.Sentry.captureMessage(String(error), {
        level: 'error',
        extra: context
    });
};

function bootstrapFrontendSentry() {
    if (!window.Sentry || window.__frontendSentryInitialized) {
        return;
    }

    const integrations = [];
    if (typeof window.Sentry.browserTracingIntegration === 'function') {
        integrations.push(window.Sentry.browserTracingIntegration());
    }

    window.Sentry.init({
        dsn: window.APP_CONFIG.SENTRY_DSN,
        environment: window.APP_CONFIG.SENTRY_ENVIRONMENT,
        release: window.APP_CONFIG.SENTRY_RELEASE || undefined,
        integrations,
        tracesSampleRate: window.APP_CONFIG.SENTRY_TRACES_SAMPLE_RATE
    });

    window.__frontendSentryInitialized = true;
}

if (window.APP_CONFIG.SENTRY_DSN && !isFileProtocol && window.location.hostname !== 'localhost') {
    if (window.Sentry) {
        bootstrapFrontendSentry();
    } else {
        const sentryScript = document.createElement('script');
        sentryScript.src = 'https://browser.sentry-cdn.com/8.28.0/bundle.tracing.min.js';
        sentryScript.crossOrigin = 'anonymous';
        sentryScript.onload = bootstrapFrontendSentry;
        document.head.appendChild(sentryScript);
    }
}
