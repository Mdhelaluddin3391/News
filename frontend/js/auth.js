// js/auth.js
const AUTH_STORAGE_KEY = 'feroxTimes_currentUser';
const BOOKMARKS_KEY = 'feroxTimes_bookmarks';
const API_BASE_URL_AUTH = CONFIG.API_BASE_URL;
const CSRF_URL = `${API_BASE_URL_AUTH}/auth/csrf/`;
const REFRESH_URL = `${API_BASE_URL_AUTH}/auth/refresh/`;
const LOGOUT_URL = `${API_BASE_URL_AUTH}/auth/logout/`;
const SAFE_HTTP_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

let csrfRequest = null;
let refreshRequest = null;

function reportAuthError(error, context = {}) {
    if (typeof window.reportFrontendError === 'function') {
        window.reportFrontendError(error, { scope: 'auth', ...context });
    }
}

function getCookie(name) {
    const cookie = document.cookie
        .split('; ')
        .find((entry) => entry.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : '';
}

function clearClientAuthState() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(BOOKMARKS_KEY);
}

async function ensureCsrfCookie(force = false) {
    if (!force && getCookie('csrftoken')) {
        return true;
    }

    if (!csrfRequest || force) {
        csrfRequest = fetch(CSRF_URL, {
            credentials: 'include'
        }).finally(() => {
            csrfRequest = null;
        });
    }

    const response = await csrfRequest;
    return response.ok;
}

async function refreshAccessSession() {
    if (refreshRequest) {
        return refreshRequest;
    }

    refreshRequest = (async () => {
        await ensureCsrfCookie();
        const headers = {};
        const csrfToken = getCookie('csrftoken');
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        const response = await fetch(REFRESH_URL, {
            method: 'POST',
            credentials: 'include',
            headers
        });

        if (!response.ok) {
            clearClientAuthState();
            if (typeof updateAuthUI === 'function') {
                updateAuthUI();
            }
        }

        return response.ok;
    })().finally(() => {
        refreshRequest = null;
    });

    return refreshRequest;
}

async function apiFetch(url, options = {}, fetchOptions = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = new Headers(options.headers || {});
    const requestOptions = {
        ...options,
        method,
        headers,
        credentials: 'include'
    };

    if (!SAFE_HTTP_METHODS.has(method)) {
        await ensureCsrfCookie();
        const csrfToken = getCookie('csrftoken');
        if (csrfToken && !headers.has('X-CSRFToken')) {
            headers.set('X-CSRFToken', csrfToken);
        }
    }

    let response = await fetch(url, requestOptions);

    if (response.status === 401 && fetchOptions.retryOnAuthFailure !== false) {
        const refreshed = await refreshAccessSession();
        if (refreshed) {
            response = await fetch(url, requestOptions);
        }
    }

    if (response.status === 401 && fetchOptions.authRequired) {
        clearClientAuthState();
        if (typeof updateAuthUI === 'function') {
            updateAuthUI();
        }
    }

    return response;
}

window.apiFetch = apiFetch;
window.ensureCsrfCookie = ensureCsrfCookie;

async function fetchCurrentUserProfile() {
    const profileRes = await apiFetch(`${API_BASE_URL_AUTH}/users/profile/`, {}, { authRequired: true });
    if (!profileRes.ok) {
        throw new Error('Could not load your profile.');
    }

    const userData = await profileRes.json();
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(userData));
    return userData;
}

async function registerUser(name, email, password) {
    try {
        const response = await apiFetch(`${API_BASE_URL_AUTH}/users/register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        }, { retryOnAuthFailure: false });
        const data = await response.json();

        if (!response.ok) {
            let errMsg = 'Registration failed.';
            if (data.email) errMsg = Array.isArray(data.email) ? data.email[0] : data.email;
            else if (data.password) errMsg = Array.isArray(data.password) ? data.password[0] : data.password;
            else if (data.name) errMsg = Array.isArray(data.name) ? data.name[0] : data.name;
            else if (data.error) errMsg = data.error;
            else if (data.detail) errMsg = data.detail;
            return { success: false, message: errMsg };
        }

        return {
            success: true,
            message: data.message || 'Registration successful. Please verify your email.',
            email: data.email || email,
            verificationRequired: data.verification_required !== false,
            emailSent: data.email_sent !== false
        };
    } catch (error) {
        reportAuthError(error, { action: 'register' });
        return { success: false, message: 'Network error. Please try again.' };
    }
}

async function loginUser(email, password) {
    try {
        const response = await apiFetch(`${API_BASE_URL_AUTH}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        }, { retryOnAuthFailure: false });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            if (data.error_code === 'email_not_verified') {
                localStorage.setItem('waitingForEmailVerification', email);
                return {
                    success: false,
                    message: 'Please verify your email first. Redirecting to verification page...',
                    needsVerification: true,
                    email
                };
            }

            return { success: false, message: data.detail || 'Invalid email or password.' };
        }

        localStorage.removeItem('waitingForEmailVerification');
        const userData = await fetchCurrentUserProfile();
        await syncBookmarks();
        return { success: true, user: userData };
    } catch (error) {
        reportAuthError(error, { action: 'login' });
        return { success: false, message: 'Network error. Please try again.' };
    }
}

async function logoutUser(options = {}) {
    const { skipRequest = false } = options;

    if (!skipRequest) {
        try {
            await ensureCsrfCookie();
            const headers = {};
            const csrfToken = getCookie('csrftoken');
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            await fetch(LOGOUT_URL, {
                method: 'POST',
                credentials: 'include',
                headers
            });
        } catch (error) {
            reportAuthError(error, { action: 'logout' });
        }
    }

    clearClientAuthState();
}

function getCurrentUser() {
    const userJson = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!userJson) {
        return null;
    }

    try {
        return JSON.parse(userJson);
    } catch (_error) {
        localStorage.removeItem(AUTH_STORAGE_KEY);
        return null;
    }
}

function updateAuthUI() {
    const user = getCurrentUser();
    const authLinks = document.querySelectorAll('.auth-link-item');
    authLinks.forEach((link) => {
        if (user) {
            if (link.classList.contains('login-link') || link.classList.contains('register-link')) link.style.display = 'none';
            if (link.classList.contains('profile-link') || link.classList.contains('saved-link') || link.classList.contains('logout-link')) link.style.display = '';
        } else {
            if (link.classList.contains('login-link') || link.classList.contains('register-link')) link.style.display = '';
            if (link.classList.contains('profile-link') || link.classList.contains('saved-link') || link.classList.contains('logout-link')) link.style.display = 'none';
        }
    });

    const userNameSpan = document.getElementById('user-name');
    if (userNameSpan) {
        userNameSpan.textContent = user ? user.name : '';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateAuthUI();
});

async function syncBookmarks() {
    if (!getCurrentUser()) {
        localStorage.removeItem(BOOKMARKS_KEY);
        return;
    }

    try {
        const res = await apiFetch(`${API_BASE_URL_AUTH}/interactions/bookmarks/`, {}, { authRequired: true });
        if (res.ok) {
            const data = await res.json();
            const bookmarks = data.results || data;
            localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks));
            return;
        }

        if (res.status === 401) {
            localStorage.removeItem(BOOKMARKS_KEY);
        }
    } catch (error) {
        reportAuthError(error, { action: 'syncBookmarks' });
    }
}

function isArticleSaved(articleId) {
    const bookmarks = JSON.parse(localStorage.getItem(BOOKMARKS_KEY) || '[]');
    return bookmarks.some((bookmark) => bookmark.article == articleId);
}

async function saveArticle(article) {
    if (!getCurrentUser()) {
        return false;
    }

    const articleId = typeof article === 'object' ? article.id : article;

    try {
        const res = await apiFetch(`${API_BASE_URL_AUTH}/interactions/bookmarks/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ article: articleId })
        }, { authRequired: true });

        if (res.ok) {
            await syncBookmarks();
            return true;
        }
    } catch (error) {
        reportAuthError(error, { action: 'saveArticle', articleId });
    }

    return false;
}

async function unsaveArticle(articleId) {
    if (!getCurrentUser()) {
        return false;
    }

    const bookmarks = JSON.parse(localStorage.getItem(BOOKMARKS_KEY) || '[]');
    const bookmark = bookmarks.find((item) => item.article == articleId);
    if (!bookmark) {
        return false;
    }

    try {
        const res = await apiFetch(`${API_BASE_URL_AUTH}/interactions/bookmarks/${bookmark.id}/`, {
            method: 'DELETE'
        }, { authRequired: true });

        if (res.ok) {
            await syncBookmarks();
            return true;
        }
    } catch (error) {
        reportAuthError(error, { action: 'unsaveArticle', articleId });
    }

    return false;
}

async function handleGoogleLogin(response) {
    const googleToken = response.credential;

    try {
        const res = await apiFetch(`${API_BASE_URL_AUTH}/users/google-login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: googleToken })
        }, { retryOnAuthFailure: false });

        const data = await res.json();

        if (!res.ok) {
            if (typeof showToast === 'function') {
                showToast(data.error || 'Google login failed.', 'error');
            }
            return;
        }

        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data.user));
        await syncBookmarks();

        const urlParams = new URLSearchParams(window.location.search);
        // ✅ SEO FIX: Redirect to clean URL root
        const redirect = urlParams.get('redirect') || '/';
        window.location.href = redirect;
    } catch (error) {
        reportAuthError(error, { action: 'googleLogin' });
        if (typeof showToast === 'function') {
            showToast('Network error during Google Login. Please try again.', 'error');
        }
    }
}
