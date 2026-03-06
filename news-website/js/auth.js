// js/auth.js
// ==================== AUTHENTICATION & API HELPERS ====================

const API_BASE_URL_AUTH = CONFIG.API_BASE_URL;
const AUTH_STORAGE_KEY = 'newsHub_currentUser';
const TOKEN_KEY = 'newsHub_accessToken';
const REFRESH_KEY = 'newsHub_refreshToken';
const BOOKMARKS_KEY = 'newsHub_bookmarks';

// Register a new user via API
async function registerUser(name, email, password) {
    try {
        const response = await fetch(`${API_BASE_URL_AUTH}/users/register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await response.json();
        
        if (!response.ok) {
            let errMsg = 'Registration failed.';
            if (data.email) errMsg = data.email[0];
            else if (data.password) errMsg = data.password[0];
            return { success: false, message: errMsg };
        }
        return { success: true };
    } catch (error) {
        return { success: false, message: 'Network error. Please try again.' };
    }
}

// Login user via JWT API
async function loginUser(email, password) {
    try {
        // 1. Get Tokens
        const response = await fetch(`${API_BASE_URL_AUTH}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();

        if (!response.ok) {
            return { success: false, message: data.detail || 'Invalid email or password.' };
        }

        // Save tokens
        localStorage.setItem(TOKEN_KEY, data.access);
        localStorage.setItem(REFRESH_KEY, data.refresh);

        // 2. Fetch User Profile Details
        const profileRes = await fetch(`${API_BASE_URL_AUTH}/users/profile/`, {
            headers: { 'Authorization': `Bearer ${data.access}` }
        });
        const userData = await profileRes.json();
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(userData));

        // 3. Sync User's Bookmarks from Backend
        await syncBookmarks();

        return { success: true, user: userData };
    } catch (error) {
        return { success: false, message: 'Network error. Please try again.' };
    }
}

// Logout user
function logoutUser() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(BOOKMARKS_KEY);
}

// Get current logged in user (Local sync function for UI)
function getCurrentUser() {
    const userJson = localStorage.getItem(AUTH_STORAGE_KEY);
    return userJson ? JSON.parse(userJson) : null;
}

// Update Header UI based on login status
function updateAuthUI() {
    const user = getCurrentUser();
    const authLinks = document.querySelectorAll('.auth-link-item');
    authLinks.forEach(link => {
        if (user) {
            if (link.classList.contains('login-link') || link.classList.contains('register-link')) link.style.display = 'none';
            if (link.classList.contains('profile-link') || link.classList.contains('saved-link') || link.classList.contains('logout-link')) link.style.display = 'inline-block';
        } else {
            if (link.classList.contains('login-link') || link.classList.contains('register-link')) link.style.display = 'inline-block';
            if (link.classList.contains('profile-link') || link.classList.contains('saved-link') || link.classList.contains('logout-link')) link.style.display = 'none';
        }
    });
    const userNameSpan = document.getElementById('user-name');
    if (userNameSpan) {
        userNameSpan.textContent = user ? user.name : '';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            logoutUser();
            updateAuthUI();
            window.location.href = 'index.html';
        });
    }
    updateAuthUI();
});

// ==================== BOOKMARKS / SAVED ARTICLES ====================

// Fetch bookmarks from Django and cache locally
async function syncBookmarks() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    try {
        const res = await fetch(`${API_BASE_URL_AUTH}/interactions/bookmarks/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            // Store array of objects [{id: 1, article: 5}, ...]
            const bookmarks = data.results || data; 
            localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks));
        }
    } catch (e) { console.error("Bookmark sync failed", e); }
}

// Check if article is saved (Synchronous for fast UI rendering)
function isArticleSaved(articleId) {
    const bookmarks = JSON.parse(localStorage.getItem(BOOKMARKS_KEY) || '[]');
    return bookmarks.some(b => b.article == articleId);
}

// Save article to Django
async function saveArticle(article) {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return false;
    
    const articleId = typeof article === 'object' ? article.id : article;

    try {
        const res = await fetch(`${API_BASE_URL_AUTH}/interactions/bookmarks/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ article: articleId })
        });
        if (res.ok) {
            await syncBookmarks(); // Refresh local cache
            return true;
        }
    } catch (e) { console.error(e); }
    return false;
}

// Delete bookmark from Django
async function unsaveArticle(articleId) {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return false;

    const bookmarks = JSON.parse(localStorage.getItem(BOOKMARKS_KEY) || '[]');
    const bookmark = bookmarks.find(b => b.article == articleId);
    if (!bookmark) return false;

    try {
        const res = await fetch(`${API_BASE_URL_AUTH}/interactions/bookmarks/${bookmark.id}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            await syncBookmarks(); // Refresh local cache
            return true;
        }
    } catch (e) { console.error(e); }
    return false;
}