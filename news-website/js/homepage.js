// ==================== HOMEPAGE.JS ====================
// Depends on auth.js, saved.js, script.js (for helpers)

const HOMEPAGE_API_URL = `${CONFIG.API_BASE_URL}/news`;

// ==================== Lazy Load Categories State ====================
let allCategoriesList = [];
let currentCategoryIndex = 0;
let isLoadingCategory = false;


// ==================== Render Functions ====================
function renderFeatured(article) {
    const container = document.getElementById('featured-news-container');
    if (!container || !article) return;

    const timeAgo = formatTimeAgo(article.published_at);
    const imageUrl = article.featured_image || 'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?ixlib=rb-4.0.3&auto=format&fit=crop&w=1170&q=80';
    const categoryName = article.category ? article.category.name : 'World';
    const authorName = article.author ? article.author.name : 'Staff';

    container.innerHTML = `
        <img src="${imageUrl}" alt="${article.title}" class="featured-image">
        <div class="featured-overlay">
            <span class="featured-category">${categoryName.toUpperCase()}</span>
            <h2 class="featured-title">${article.title}</h2>
            <div class="featured-meta">
                <span><i class="far fa-clock"></i> ${timeAgo}</span>
                <span><i class="far fa-user"></i> By ${authorName}</span>
                <span><i class="far fa-eye"></i> ${article.views || 0} views</span>
            </div>
        </div>
    `;
    // Add click event to open article
    container.addEventListener('click', () => {
        window.location.href = `article.html?id=${article.id}`;
    });
}

function renderTrending(trending) {
    const container = document.getElementById('trending-container');
    if (!container) return;

    if (trending.length === 0) {
        container.innerHTML = '<p style="color: var(--gray); font-size: 0.9rem;">No trending news.</p>';
        return;
    }

    let html = '';
    trending.forEach((item, index) => {
        const number = (index + 1).toString().padStart(2, '0');
        const categoryName = item.category ? item.category.name : 'News';

        html += `
            <div class="trending-news-item" data-id="${item.id}">
                <div class="trending-number">${number}</div>
                <div class="trending-content">
                    <h4>${item.title}</h4>
                    <div class="trending-category">${categoryName.toUpperCase()}</div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;

    container.querySelectorAll('.trending-news-item').forEach(item => {
        item.addEventListener('click', () => {
            const id = item.dataset.id;
            window.location.href = `article.html?id=${id}`;
        });
    });
}

function renderCategories(categories) {
    const container = document.getElementById('categories-container');
    if (!container) return;

    let html = '';
    categories.forEach(cat => {
        html += `
            <li><a href="index.html?category=${cat.slug}">${cat.name}</a></li>
        `;
    });
    container.innerHTML = html;
}

function renderBreakingTicker(messages) {
    const container = document.getElementById('breaking-ticker-content');
    if (!container) return;

    if (messages && messages.length > 0) {
        container.textContent = '• ' + messages.join(' • ');
    } else {
        container.textContent = 'Welcome to NewsHub!';
    }
}

// Render Editor's Picks
function renderEditorsPicks(picks) {
    const container = document.getElementById('editors-picks-container');
    if (!container) return;

    if (!picks || picks.length === 0) {
        container.innerHTML = '<p style="color: var(--gray); font-size: 0.9rem;">No editor picks available at the moment.</p>';
        return;
    }

    let html = '';
    picks.forEach(item => {
        const imageUrl = item.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=150&q=80';
        
        html += `
            <div class="side-post" onclick="window.location.href='article.html?id=${item.id}'" style="margin-bottom: 15px; cursor: pointer;">
                <img src="${imageUrl}" alt="${item.title}">
                <div class="side-post-content">
                    <h4 style="font-size: 0.95rem;">${item.title}</h4>
                    <span class="side-meta"><i class="far fa-clock"></i> ${formatTimeAgo(item.published_at)}</span>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

// ==================== GLOBAL SIDEBAR LOADING FUNCTIONS ====================
// Inhein 'window' par isliye rakha hai taaki script.js har page par inhein call kar sake

window.loadEditorsPicks = async function() {
    try {
        const res = await fetch(`${HOMEPAGE_API_URL}/articles/?is_editors_pick=true`);
        const data = await res.json();
        renderEditorsPicks(data.results || data);
    } catch (err) {
        console.error("Error loading Editor's Picks:", err);
    }
};

window.loadTrendingNews = async function() {
    try {
        const res = await fetch(`${HOMEPAGE_API_URL}/articles/?is_trending=true`);
        const data = await res.json();
        renderTrending(data.results || data);
    } catch (err) {
        console.error("Error loading Trending News:", err);
    }
};

window.loadCategoriesSidebar = async function() {
    try {
        const res = await fetch(`${HOMEPAGE_API_URL}/categories/`);
        const data = await res.json();
        renderCategories(data.results || data);
    } catch (err) {
        console.error("Error loading Categories Sidebar:", err);
    }
};

// ==================== Helper: time ago ====================
function formatTimeAgo(isoString) {
    if (!isoString) return 'Just now';
    const now = new Date();
    const past = new Date(isoString);
    const diffMs = now - past;
    const diffHrs = Math.floor(diffMs / 3600000);
    if (diffHrs < 1) return 'Just now';
    if (diffHrs < 24) return `${diffHrs} hour${diffHrs > 1 ? 's' : ''} ago`;
    const diffDays = Math.floor(diffHrs / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

// ==================== Load Categories in Batches (Lazy Loading) ====================
async function loadNextCategories(count = 1) {
    if (isLoadingCategory || currentCategoryIndex >= allCategoriesList.length) return;
    
    isLoadingCategory = true;
    const scrollLoader = document.getElementById('category-scroll-loader');
    if (scrollLoader) scrollLoader.style.display = 'block';

    const container = document.getElementById('home-categories-container');
    let html = '';

    const endIndex = Math.min(currentCategoryIndex + count, allCategoriesList.length);

    for (let i = currentCategoryIndex; i < endIndex; i++) {
        const cat = allCategoriesList[i];
        try {
            const artRes = await fetch(`${HOMEPAGE_API_URL}/articles/?category__slug=${cat.slug}`);
            const artData = await artRes.json();
            const articles = (artData.results || artData).slice(0, 5);

            if (articles.length === 0) continue;

            const mainArticle = articles[0];
            const sideArticles = articles.slice(1, 5);

            let sideHtml = sideArticles.map(a => `
                <div class="side-post" onclick="window.location.href='article.html?id=${a.id}'">
                    <img src="${a.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=150&q=80'}" alt="${a.title}">
                    <div class="side-post-content">
                        <h4>${a.title}</h4>
                        <span class="side-meta"><i class="far fa-clock"></i> ${formatTimeAgo(a.published_at)}</span>
                    </div>
                </div>
            `).join('');

            html += `
                <div class="category-block">
                    <h2 class="category-heading" style="margin-top: 1rem; margin-bottom: 1.5rem; font-size: 1.8rem;">
                        <a href="index.html?category=${cat.slug}" style="text-decoration:none; color:inherit; display:flex; justify-content:space-between; align-items:center;">
                            ${cat.name} 
                            <span style="font-size:0.9rem; color:var(--primary); font-family:'Roboto', sans-serif;">View All →</span>
                        </a>
                    </h2>
                    <div class="category-grid">
                        <div class="main-post" onclick="window.location.href='article.html?id=${mainArticle.id}'">
                            <img src="${mainArticle.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80'}" alt="${mainArticle.title}">
                            <div class="main-post-content">
                                <h3>${mainArticle.title}</h3>
                                <p>${mainArticle.description ? (mainArticle.description.length > 110 ? mainArticle.description.substring(0, 110) + '...' : mainArticle.description) : ''}</p>
                                <span class="main-meta"><i class="far fa-clock"></i> ${formatTimeAgo(mainArticle.published_at)}</span>
                            </div>
                        </div>
                        <div class="side-posts">
                            ${sideHtml}
                        </div>
                    </div>
                </div>
            `;
        } catch (e) {
            console.error(`Error loading category ${cat.name}`, e);
        }
    }

    if(container) container.insertAdjacentHTML('beforeend', html);
    
    currentCategoryIndex = endIndex;
    isLoadingCategory = false;
    if (scrollLoader) scrollLoader.style.display = 'none';
}

function setupScrollObserver() {
    const scrollLoader = document.getElementById('category-scroll-loader');
    if (!scrollLoader) return;

    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            loadNextCategories(1);
        }
    }, { root: null, rootMargin: '100px', threshold: 0.1 });

    observer.observe(scrollLoader);
}


// ==================== Initialize Homepage ====================
async function initHomepage() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const currentCategory = urlParams.get('category') || 'general';

        // Sidebar data ab hamare global functions se load hoga (Clean code)
        window.loadEditorsPicks();
        window.loadTrendingNews();
        window.loadCategoriesSidebar();

        const [featuredRes, breakingRes, categoriesRes] = await Promise.all([
            fetch(`${HOMEPAGE_API_URL}/articles/?is_featured=true`),
            fetch(`${HOMEPAGE_API_URL}/articles/?is_breaking=true`),
            fetch(`${HOMEPAGE_API_URL}/categories/`)
        ]);

        const featuredData = await featuredRes.json();
        const breakingData = await breakingRes.json();
        const categoriesData = await categoriesRes.json();
        
        const categoriesList = categoriesData.results || categoriesData;

        // Render Top Featured
        if (featuredData.results && featuredData.results.length > 0) {
            renderFeatured(featuredData.results[0]);
        }

        // Render Breaking News Ticker
        const breakingTitles = (breakingData.results || []).map(item => item.title);
        renderBreakingTicker(breakingTitles);

        // Render Category Blocks (Lazy Loading Setup)
        if (currentCategory === 'general') {
            allCategoriesList = categoriesList;
            currentCategoryIndex = 0;
            const homeContainer = document.getElementById('home-categories-container');
            if(homeContainer) {
                homeContainer.innerHTML = ''; 
                await loadNextCategories(2); 
                setupScrollObserver();
            }
            
            // Homepage SEO Update
            if (typeof updateSEOMetaTags === 'function') {
                updateSEOMetaTags(
                    'NewsHub - Premium Global News', 
                    'Stay updated with the latest breaking news, trending stories, and in-depth articles from around the world on NewsHub.', 
                    'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?auto=format&fit=crop&w=1200&q=80', 
                    window.location.href
                );
            }
            
            // === NAYA: Custom Push Notification Prompt ===
            // Page load hone ke 4 second baad custom popup dikhayenge
            setTimeout(() => {
                showCustomPushPrompt();
            }, 4000); 
            // ============================================
        }

    } catch (error) {
        console.error('Error fetching homepage data:', error);
    }
}

// ==================== Custom Push Notification Prompt ====================
function showCustomPushPrompt() {
    // 1. Agar browser support nahi karta, toh wapas jao
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    
    // 2. Agar permission pehle se Granted ya Denied hai, toh popup mat dikhao
    if (Notification.permission !== 'default') return;

    // 3. Agar user ne pehle "Maybe Later" click kiya tha, toh usko pareshaan mat karo
    if (localStorage.getItem('push_prompt_dismissed') === 'true') return;

    // 4. Custom HTML Popup Banayein (Jo bottom-left corner me smoothly aayega)
    const promptDiv = document.createElement('div');
    promptDiv.id = 'custom-push-prompt';
    promptDiv.innerHTML = `
        <div style="position: fixed; bottom: 20px; left: 20px; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); z-index: 9999; max-width: 350px; border-left: 5px solid var(--primary); font-family: 'Roboto', sans-serif; animation: slideInUp 0.5s ease-out;">
            <h4 style="margin: 0 0 10px 0; color: var(--dark); font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-bell" style="color: var(--secondary);"></i> 
                Get Breaking News Alerts!
            </h4>
            <p style="margin: 0 0 15px 0; font-size: 0.95rem; color: var(--gray); line-height: 1.5;">
                Subscribe to get notified instantly about major breaking news and featured stories.
            </p>
            <div style="display: flex; gap: 10px;">
                <button id="push-allow-btn" style="background: var(--primary); color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; font-weight: 600; flex: 1; transition: background 0.3s;">
                    Allow Alerts
                </button>
                <button id="push-dismiss-btn" style="background: #f1f5f9; color: #475569; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; font-weight: 500; flex: 1; transition: background 0.3s;">
                    Maybe Later
                </button>
            </div>
        </div>
        <style>
            @keyframes slideInUp {
                from { transform: translateY(100px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            #push-allow-btn:hover { background: var(--primary-dark) !important; }
            #push-dismiss-btn:hover { background: #e2e8f0 !important; }
        </style>
    `;
    
    document.body.appendChild(promptDiv);

    // 5. Jab user "Allow Alerts" par click kare
    document.getElementById('push-allow-btn').addEventListener('click', () => {
        promptDiv.remove(); // Custom UI hatao
        
        // Ab actual browser ka notification prompt trigger hoga jo push-notifications.js mein hai
        if (typeof subscribeToPush === 'function') {
            subscribeToPush(); 
        } else {
            console.error("subscribeToPush function is not defined. Make sure push-notifications.js is loaded.");
        }
    });

    // 6. Jab user "Maybe Later" par click kare
    document.getElementById('push-dismiss-btn').addEventListener('click', () => {
        promptDiv.remove(); // Custom UI hatao
        // Local storage mein save kar lo taaki baar-baar user ko pareshaan na karein
        localStorage.setItem('push_prompt_dismissed', 'true'); 
    });
}

// ==================== Newsletter Form Listener ====================
const newsletterForm = document.getElementById('newsletterForm');
if (newsletterForm) {
    newsletterForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = newsletterForm.querySelector('input[type="email"]').value;
        const btn = newsletterForm.querySelector('button');

        btn.disabled = true;
        btn.textContent = 'Subscribing...';

        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/newsletter/subscribe/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            });

            const data = await response.json();

            if (response.ok) {
                if(typeof showToast === 'function') showToast(data.message || 'Thank you for subscribing!', 'success');
                else alert(data.message || 'Thank you for subscribing!');
                newsletterForm.reset();
            } else {
                if(typeof showToast === 'function') showToast(data.error || 'Subscription failed.', 'error');
                else alert(data.error || 'Subscription failed.');
            }
        } catch (err) {
            console.error(err);
            alert('Network Error. Please try again later.');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Subscribe Now';
        }
    });
}