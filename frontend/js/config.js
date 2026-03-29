const APP_CONFIG = window.__APP_CONFIG__ || {};
const isFileProtocol = window.location.protocol === 'file:';

// For production with Nginx gateway, use relative paths
// For development with separate servers, this will still work
const apiBaseUrl = 'http://0.0.0.0:8000/api';

const CONFIG = {
    API_BASE_URL: apiBaseUrl,
    GOOGLE_CLIENT_ID: APP_CONFIG.GOOGLE_CLIENT_ID || '615098838513-hnphi7ekcv9nhjv94f0mfj0509nd63hu.apps.googleusercontent.com',
    VAPID_PUBLIC_KEY: APP_CONFIG.VAPID_PUBLIC_KEY || 'BL_wQ4AU0MABrcB7uQc5dX7d725RZmGktXdlp9YD6m1MWopxpFcFMLjiBdF8pMjuAKOJmwX4a596wC0mj4HlMQ8',
    SENTRY_DSN: APP_CONFIG.SENTRY_DSN || '',
    SENTRY_ENVIRONMENT: APP_CONFIG.SENTRY_ENVIRONMENT || (window.location.hostname === 'localhost' || isFileProtocol ? 'development' : 'production'),
    SENTRY_RELEASE: APP_CONFIG.SENTRY_RELEASE || '',
    SENTRY_TRACES_SAMPLE_RATE: Number(APP_CONFIG.SENTRY_TRACES_SAMPLE_RATE || 0)
};

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
        dsn: CONFIG.SENTRY_DSN,
        environment: CONFIG.SENTRY_ENVIRONMENT,
        release: CONFIG.SENTRY_RELEASE || undefined,
        integrations,
        tracesSampleRate: CONFIG.SENTRY_TRACES_SAMPLE_RATE
    });

    window.__frontendSentryInitialized = true;
}

if (CONFIG.SENTRY_DSN && !isFileProtocol && !isLocalHost) {
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
