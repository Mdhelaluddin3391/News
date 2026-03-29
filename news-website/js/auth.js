const AUTH_STORAGE_KEY = 'forexTimes_currentUser';
const TOKEN_KEY = 'forexTimes_accessToken';
const REFRESH_KEY = 'forexTimes_refreshToken';
const BOOKMARKS_KEY = 'forexTimes_bookmarks';
const API_BASE_URL_AUTH = CONFIG.API_BASE_URL;

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
        return { success: false, message: 'Network error. Please try again.' };
    }
}

async function loginUser(email, password) {
    try {
        const response = await fetch(`${API_BASE_URL_AUTH}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();

        if (!response.ok) {
            // Check if error is due to unverified email
            if (data.error_code === 'email_not_verified') {
                localStorage.setItem('waitingForEmailVerification', email);
                return { 
                    success: false, 
                    message: 'Please verify your email first. Redirecting to verification page...',
                    needsVerification: true,
                    email: email
                };
            }
            return { success: false, message: data.detail || 'Invalid email or password.' };
        }

        localStorage.setItem(TOKEN_KEY, data.access);
        localStorage.setItem(REFRESH_KEY, data.refresh);

        const profileRes = await fetch(`${API_BASE_URL_AUTH}/users/profile/`, {
            headers: { 'Authorization': `Bearer ${data.access}` }
        });
        const userData = await profileRes.json();
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(userData));

        await syncBookmarks();
        return { success: true, user: userData };
    } catch (error) {
        return { success: false, message: 'Network error. Please try again.' };
    }
}

function logoutUser() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(BOOKMARKS_KEY);
}

function getCurrentUser() {
    const userJson = localStorage.getItem(AUTH_STORAGE_KEY);
    return userJson ? JSON.parse(userJson) : null;
}

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
    updateAuthUI();
});

async function syncBookmarks() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    try {
        const res = await fetch(`${API_BASE_URL_AUTH}/interactions/bookmarks/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            const bookmarks = data.results || data; 
            localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks));
        }
    } catch (e) { console.error(e); }
}

function isArticleSaved(articleId) {
    const bookmarks = JSON.parse(localStorage.getItem(BOOKMARKS_KEY) || '[]');
    return bookmarks.some(b => b.article == articleId);
}

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
            await syncBookmarks();
            return true;
        }
    } catch (e) { console.error(e); }
    return false;
}

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
            await syncBookmarks();
            return true;
        }
    } catch (e) { console.error(e); }
    return false;
}


async function handleGoogleLogin(response) {
    const googleToken = response.credential;
    
    try {
        const res = await fetch(`${API_BASE_URL_AUTH}/users/google-login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: googleToken })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            alert(data.error || 'Google login failed.');
            return;
        }

        // Backend ne hume access/refresh tokens de diye hain
        localStorage.setItem(TOKEN_KEY, data.access);
        localStorage.setItem(REFRESH_KEY, data.refresh);
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data.user));

        await syncBookmarks();
        
        // Login successful, redirect to home or previous page
        const urlParams = new URLSearchParams(window.location.search);
        const redirect = urlParams.get('redirect') || 'index.html';
        window.location.href = redirect;

    } catch (error) {
        console.error('Google login network error:', error);
        alert('Network error during Google Login. Please try again.');
    }
}
