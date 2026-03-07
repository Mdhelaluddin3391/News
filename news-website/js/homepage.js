// ==================== HOMEPAGE.JS ====================
// Depends on auth.js, saved.js, script.js (for helpers)

const HOMEPAGE_API_URL = `${CONFIG.API_BASE_URL}/news`;

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

// Helper: time ago
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

// ==================== NEW: Render All Categories Top 5 ====================
async function renderAllCategoriesTop5(categories) {
    const container = document.getElementById('home-categories-container');
    if (!container) return;

    let html = '';

    for (const cat of categories) {
        try {
            // Fetch latest articles for this category
            const artRes = await fetch(`${HOMEPAGE_API_URL}/articles/?category__slug=${cat.slug}`);
            const artData = await artRes.json();
            const articles = (artData.results || artData).slice(0, 5); // Take exactly up to 5

            if (articles.length === 0) continue; // Skip empty categories

            const mainArticle = articles[0]; // 1 Featured post
            const sideArticles = articles.slice(1, 5); // Next 4 posts

            // Build side posts HTML
            let sideHtml = sideArticles.map(a => `
                <div class="side-post" onclick="window.location.href='article.html?id=${a.id}'">
                    <img src="${a.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=150&q=80'}" alt="${a.title}">
                    <div class="side-post-content">
                        <h4>${a.title}</h4>
                        <span class="side-meta"><i class="far fa-clock"></i> ${formatTimeAgo(a.published_at)}</span>
                    </div>
                </div>
            `).join('');

            // Build full block HTML
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
                                <p>${mainArticle.description ? mainArticle.description.substring(0, 100) + '...' : ''}</p>
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

    container.innerHTML = html;
}

// ==================== Initialize Homepage ====================
async function initHomepage() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const currentCategory = urlParams.get('category') || 'general';

        const [featuredRes, trendingRes, breakingRes, categoriesRes] = await Promise.all([
            fetch(`${HOMEPAGE_API_URL}/articles/?is_featured=true`),
            fetch(`${HOMEPAGE_API_URL}/articles/?is_trending=true`),
            fetch(`${HOMEPAGE_API_URL}/articles/?is_breaking=true`),
            fetch(`${HOMEPAGE_API_URL}/categories/`)
        ]);

        const featuredData = await featuredRes.json();
        const trendingData = await trendingRes.json();
        const breakingData = await breakingRes.json();
        const categoriesData = await categoriesRes.json();
        const categoriesList = categoriesData.results || categoriesData;

        // Render Top Featured
        if (featuredData.results && featuredData.results.length > 0) {
            renderFeatured(featuredData.results[0]);
        }

        // Render Trending Sidebar
        renderTrending(trendingData.results || []);

        // Render Categories Sidebar
        renderCategories(categoriesList);

        // Render Breaking News Ticker
        const breakingTitles = (breakingData.results || []).map(item => item.title);
        renderBreakingTicker(breakingTitles);

        // Render Category Blocks (Only if we are on the Homepage / General)
        if (currentCategory === 'general') {
            await renderAllCategoriesTop5(categoriesList);
        }

    } catch (error) {
        console.error('Error fetching homepage data:', error);
    }
}

// Run when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof updateAuthUI === 'function') updateAuthUI();
    initHomepage();

    const newsletterForm = document.getElementById('newsletterForm');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = newsletterForm.querySelector('input[type="email"]').value;
            const btn = newsletterForm.querySelector('button');

            btn.disabled = true;
            btn.textContent = 'Subscribing...';

            try {
                alert(`Thank you for subscribing with: ${email}\nYou'll receive our newsletter shortly.`);
                newsletterForm.reset();
            } catch (err) {
                alert('Error subscribing. Please try again.');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Subscribe Now';
            }
        });
    }

    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navLinks = document.querySelector('.nav-links');
    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }
});