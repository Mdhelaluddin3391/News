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
    // NAYA CODE: Global helper function for image URL
    const imageUrl = window.getFullImageUrl(article.featured_image, 'images/default-news.png');
    const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
    const categoryName = article.category ? article.category.name : 'World';
    const authorName = article.author ? article.author.name : 'Staff';
    const liveBadgeHTML = article.is_live ? `<div class="live-badge-card"><i class="fas fa-circle"></i> LIVE</div>` : '';

    container.innerHTML = `
        ${liveBadgeHTML}
        <img src="${imageUrl}" alt="${article.title}" class="featured-image ${containClass}">
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
        window.location.href = `/article.html?slug=${article.slug}`;
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
            <div class="trending-news-item" data-slug="${item.slug}">
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
            const slug = item.dataset.slug || item.dataset.id;
            window.location.href = `/article.html?slug=${slug}`;
        });
    });
}

function renderCategories(categories) {
    const container = document.getElementById('categories-container');
    if (!container) return;

    let html = '';
    categories.forEach(cat => {
        html += `
            <li><a href="/?category=${cat.slug}">${cat.name}</a></li>
        `;
    });
    container.innerHTML = html;
}

function renderBreakingTicker(articles) {
    const container = document.getElementById('breaking-ticker-content');
    if (!container) return;

    if (articles && articles.length > 0) {
        // Har article ke liye ek clickable link banayein
        const html = articles.map(article => 
            `<a href="/article?slug=${article.slug}" class="breaking-link">${article.title}</a>`
        ).join(' &nbsp;&bull;&nbsp; '); // Beech mein ek dot (•) laga rahe hain
        
        container.innerHTML = html;
    } else {
        container.innerHTML = 'Welcome to Ferox Times!';
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
        // NAYA CODE: Global helper function for image URL
        const imageUrl = window.getFullImageUrl(item.featured_image, 'images/default-news.png');
        const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
        
        html += `
            <div class="side-post" onclick="window.location.href=\'/article?slug=${item.slug}\'" style="margin-bottom: 15px; cursor: pointer;">
                <img src="${imageUrl}" alt="${item.title}" class="${containClass}">
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

            let sideHtml = sideArticles.map(a => {
                const sideLiveBadge = a.is_live ? `<div class="live-badge-card" style="padding: 2px 5px; font-size: 0.6rem; top: 5px; left: 5px;"><i class="fas fa-circle" style="font-size: 6px;"></i> LIVE</div>` : '';
                // NAYA CODE: Global helper function for image URL
                const sideImageUrl = window.getFullImageUrl(a.featured_image, 'images/default-news.png');
                const sideContainClass = sideImageUrl.includes('default-news.png') ? 'img-contain' : '';
                return `
                <div class="side-post" onclick="window.location.href='/article.html?slug=${a.slug}'" style="position: relative;">
                    ${sideLiveBadge}
                    <img src="${sideImageUrl}" alt="${a.title}" class="${sideContainClass}">
                    <div class="side-post-content">
                        <h4>${a.title}</h4>
                        <span class="side-meta"><i class="far fa-clock"></i> ${formatTimeAgo(a.published_at)}</span>
                    </div>
                </div>
                `;
            }).join('');


            const mainLiveBadge = mainArticle.is_live ? `<div class="live-badge-card"><i class="fas fa-circle"></i> LIVE</div>` : '';
            // NAYA CODE: Global helper function for image URL
            const mainImageUrl = window.getFullImageUrl(mainArticle.featured_image, 'images/default-news.png');
            const containClass = mainImageUrl.includes('default-news.png') ? 'img-contain' : '';

            html += `
                <div class="category-block">
                    <h2 class="category-heading" style="margin-top: 1rem; margin-bottom: 1.5rem; font-size: 1.8rem;">
                        <a href="/?category=${cat.slug}" style="text-decoration:none; color:inherit; display:flex; justify-content:space-between; align-items:center;">
                            ${cat.name} 
                            <span style="font-size:0.9rem; color:var(--primary); font-family:'Roboto', sans-serif;">View All →</span>
                        </a>
                    </h2>
                    <div class="category-grid">
                        <div class="main-post" onclick="window.location.href='/article.html?slug=${mainArticle.slug}'">
                            ${mainLiveBadge}
                            <img src="${mainImageUrl}" alt="${mainArticle.title}" class="${containClass}">
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
        // window.loadTopStories()
        window.loadEditorsPicks();
        window.loadTrendingNews();
        window.loadCategoriesSidebar();
        window.loadWebStories();

        // NAYA: 4th API call 'recentRes' add kiya gaya hai latest articles ke liye
        const [featuredRes, breakingRes, categoriesRes, recentRes] = await Promise.all([
            fetch(`${HOMEPAGE_API_URL}/articles/?is_featured=true`),
            fetch(`${HOMEPAGE_API_URL}/articles/?is_breaking=true`),
            fetch(`${HOMEPAGE_API_URL}/categories/`),
            fetch(`${HOMEPAGE_API_URL}/articles/`) // Default list returns the latest articles
        ]);

        const featuredData = await featuredRes.json();
        const breakingData = await breakingRes.json();
        const categoriesData = await categoriesRes.json();
        const recentData = await recentRes.json(); // NAYA: Recent news data
        
        const categoriesList = categoriesData.results || categoriesData;

        // Render Top Featured
        if (featuredData.results && featuredData.results.length > 0) {
            // 1. Pehle check karo ki featured list mein koi aisi news hai kya jo LIVE bhi ho?
            const liveFeaturedArticle = featuredData.results.find(article => article.is_live === true);
            
            if (liveFeaturedArticle) {
                // Agar LIVE + FEATURED news mili, toh usko sabse top priority do
                renderFeatured(liveFeaturedArticle);
            } else {
                // Agar koi LIVE news nahi hai, toh bas normal sabse latest featured news dikha do
                renderFeatured(featuredData.results[0]);
            }
        }

        // Render Breaking News Ticker
        const breakingArticles = breakingData.results || breakingData;
        renderBreakingTicker(breakingArticles);

        // === NAYA CODE: Render 5 Recent News ===
        if (recentData.results) {
            renderRecentNews(recentData.results.slice(0, 5));
        } else if (Array.isArray(recentData)) {
            renderRecentNews(recentData.slice(0, 5));
        }
        // =======================================

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
                    'Ferox Times - Premium Global News', 
                    'Stay updated with the latest breaking news, trending stories, and in-depth articles from around the world on Ferox Times.', 
                    'images/default-news.png', 
                    window.location.href,
                    "global news, breaking news, latest updates, world news, Ferox Times" // <-- NAYA: Keywords add kiye
                );
            }

            // === NAYA CODE: HOMEPAGE SCHEMA MARKUP ===
            if (typeof injectSchema === 'function') {
                const homepageSchema = {
                    "@context": "https://schema.org",
                    "@graph": [
                        {
                            "@type": "WebSite",
                            "name": "Ferox Times",
                            "url": "https://www.feroxtimes.com/", // Apna actual domain use karein
                            "potentialAction": {
                                "@type": "SearchAction",
                                "target": "https://www.feroxtimes.com/search?q={search_term_string}",
                                "query-input": "required name=search_term_string"
                            }
                        },
                        {
                            "@type": "Organization",
                            "name": "Ferox Times",
                            "url": "https://www.feroxtimes.com/",
                            "logo": "https://www.feroxtimes.com/images/logo.png", // Apne logo ka sahi URL daalein
                            "sameAs": [
                                "https://www.facebook.com/feroxtimes",
                                "https://twitter.com/feroxtimes"
                            ]
                        }
                    ]
                };
                injectSchema(homepageSchema);
            }
            // ===========================================
            
            // Custom Push Notification Prompt
            setTimeout(() => {
                showCustomPushPrompt();
            }, 4000); 
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
                Subscribe to get notified instantly about all our latest articles and breaking news!
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




// ==================== NAYA CODE: Render Recent News ====================
function renderRecentNews(articles) {
    const section = document.getElementById('recent-news-section');
    const container = document.getElementById('recent-news-container');
    if (!container || !section) return;

    if (!articles || articles.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    let html = '';

    articles.forEach(article => {
        const timeAgo = formatTimeAgo(article.published_at);
        // NAYA CODE: Global helper function for image URL
        const imageUrl = window.getFullImageUrl(article.featured_image, 'images/default-news.png');
        const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
        const liveBadge = article.is_live ? `<div class="live-badge-card" style="padding: 2px 4px; font-size: 0.65rem; top: 5px; left: 5px;"><i class="fas fa-circle" style="font-size: 6px;"></i> LIVE</div>` : '';

        html += `
            <div class="recent-news-card" onclick="window.location.href='/article.html?slug=${article.slug}'" style="position: relative; min-width: 160px; width: 160px; cursor: pointer; flex-shrink: 0; background: var(--card-bg); border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid var(--border); transition: transform 0.2s ease;">
                ${liveBadge}
                <img src="${imageUrl}" alt="${article.title}" class="${containClass}" style="width: 100%; height: 100px; object-fit: cover; border-bottom: 1px solid var(--border);">
                <div style="padding: 12px 10px;">
                    <h4 style="font-size: 0.85rem; margin-bottom: 8px; line-height: 1.4; color: var(--dark); font-family: 'Roboto', sans-serif; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${article.title}</h4>
                    <span style="font-size: 0.75rem; color: var(--secondary); font-weight: 600;"><i class="far fa-clock"></i> ${timeAgo}</span>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    
    // Hover effect dynamically add karne ke liye
    const cards = container.querySelectorAll('.recent-news-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-3px)';
            card.style.boxShadow = '0 6px 12px rgba(0,0,0,0.15)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'none';
            card.style.boxShadow = '0 2px 5px rgba(0,0,0,0.1)';
        });
    });
}
// =========================================================================


// ==================== NAYA CODE: Render Top Stories ====================
function renderTopStories(stories) {
    const container = document.getElementById('top-stories-container');
    if (!container) return;

    if (!stories || stories.length === 0) {
        container.innerHTML = '<p style="color: var(--gray); font-size: 0.9rem;">No top stories at the moment.</p>';
        return;
    }

    let html = '';
    stories.forEach((item, index) => {
        const number = (index + 1).toString().padStart(2, '0');
        const categoryName = item.category ? item.category.name : 'News';

        // Isko Trending jaisa ek sundar numbered list format diya hai
        html += `
            <div class="trending-news-item" data-slug="${item.slug}" style="cursor: pointer;">
                <div class="trending-number" style="color: var(--primary); font-size: 1.8rem;">${number}</div>
                <div class="trending-content">
                    <h4 style="font-size: 0.95rem; margin-bottom: 5px;">${item.title}</h4>
                    <div class="trending-category" style="font-size: 0.75rem;">${categoryName.toUpperCase()}</div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;

    // Click event add karne ke liye
    container.querySelectorAll('.trending-news-item').forEach(item => {
        item.addEventListener('click', () => {
            const slug = item.dataset.slug || item.dataset.id;
            window.location.href = `/article.html?slug=${slug}`;
        });
    });
}

// Global fetch function for Top Stories
window.loadTopStories = async function() {
    try {
        const res = await fetch(`${HOMEPAGE_API_URL}/articles/?is_top_story=true`);
        const data = await res.json();
        renderTopStories(data.results || data);
    } catch (err) {
        console.error("Error loading Top Stories:", err);
    }
};




// ==================== DYNAMIC WEB STORIES (SHORTS) ====================

let dynamicStories = [];
let currentStoryIndex = 0;
let storyTimer;
const STORY_DURATION = 5000; // 5 seconds per story

// 1. Backend se Web Stories Fetch karna
window.loadWebStories = async function() {
    try {
        const res = await fetch(`${HOMEPAGE_API_URL}/articles/?is_web_story=true`);
        const data = await res.json();
        dynamicStories = data.results || data;

        // Agar koi story nahi hai toh section hide kar do
        const storySection = document.querySelector('.web-stories-section');
        if (dynamicStories.length === 0) {
            if (storySection) storySection.style.display = 'none';
            return;
        } else {
            if (storySection) storySection.style.display = 'block';
        }

        renderStoryThumbnails();
    } catch (err) {
        console.error("Error loading Web Stories:", err);
    }
};

// 2. Thumbnails Render karna
function renderStoryThumbnails() {
    const container = document.getElementById('story-thumbnails-container');
    if (!container) return;

    let html = '';
    dynamicStories.forEach((story, index) => {
        // Production ready image URL
        const imageUrl = window.getFullImageUrl(story.featured_image, 'images/default-news.png');
        const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
        
        html += `
            <div class="story-thumb" onclick="openStoryModal(${index})">
                <div class="story-thumb-inner">
                    <img src="${imageUrl}" alt="${story.title}" class="${containClass}">
                    <div class="story-thumb-overlay">
                        <div class="story-thumb-title">${story.title}</div>
                    </div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

// 3. Modal Open karna
function openStoryModal(index) {
    currentStoryIndex = index;
    document.getElementById('story-modal').style.display = 'flex';
    document.body.classList.add('no-scroll');
    showStory();
}

// 4. Modal Close karna
function closeStoryModal() {
    document.getElementById('story-modal').style.display = 'none';
    document.body.classList.remove('no-scroll');
    clearTimeout(storyTimer);
    document.getElementById('story-progress-bar').style.transition = 'none';
    document.getElementById('story-progress-bar').style.width = '0%';
}

// 5. Story Show karna
function showStory() {
    if (dynamicStories.length === 0) return;
    
    const story = dynamicStories[currentStoryIndex];
    const display = document.getElementById('story-display');
    const progressBar = document.getElementById('story-progress-bar');
    
    const imageUrl = window.getFullImageUrl(story.featured_image, 'images/default-news.png');
    const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
    const categoryName = story.category ? story.category.name : 'News';
    const shortDesc = story.description ? (story.description.length > 100 ? story.description.substring(0, 100) + '...' : story.description) : '';
    
    display.innerHTML = `
        <img src="${imageUrl}" alt="Story" class="${containClass}">
        <div class="story-text-container">
            <span class="story-badge">${categoryName}</span>
            <h2 class="story-modal-title">${story.title}</h2>
            <p class="story-modal-desc">${shortDesc}</p>
            <a href="/article.html?slug=${story.slug}" class="story-read-more">Swipe up or Click to Read More</a>
        </div>
    `;

    // Progress Bar Animation Reset & Start
    progressBar.style.transition = 'none';
    progressBar.style.width = '0%';
    
    setTimeout(() => {
        progressBar.style.transition = `width ${STORY_DURATION}ms linear`;
        progressBar.style.width = '100%';
    }, 50);

    clearTimeout(storyTimer);
    storyTimer = setTimeout(() => {
        nextStory();
    }, STORY_DURATION);
}

// 6. Navigation
function nextStory() {
    if (currentStoryIndex < dynamicStories.length - 1) {
        currentStoryIndex++;
        showStory();
    } else {
        closeStoryModal();
    }
}

function prevStory() {
    if (currentStoryIndex > 0) {
        currentStoryIndex--;
        showStory();
    } else {
        showStory(); // Restart same story
    }
}

// Setup Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    const closeBtn = document.getElementById('close-story-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeStoryModal);
    }
});



// ==================== GLOBAL BREAKING NEWS FUNCTION ====================
window.loadBreakingNews = async function() {
    try {
        const res = await fetch(`${HOMEPAGE_API_URL}/articles/?is_breaking=true`);
        const data = await res.json();
        const breakingArticles = data.results || data;
        renderBreakingTicker(breakingArticles);
    } catch (err) {
        console.error("Error loading Breaking News:", err);
    }
};