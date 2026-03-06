// ==================== HOMEPAGE.JS ====================
// Depends on auth.js, saved.js, script.js (for helpers)

const API_BASE_URL = `${CONFIG.API_BASE_URL}/news`; // Backend URL

// ==================== Render Functions ====================
function renderFeatured(article) {
    const container = document.getElementById('featured-news-container');
    if (!container || !article) return;

    const timeAgo = formatTimeAgo(article.published_at);
    // Backend se image link aayega, warna placeholder show hoga
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

function renderGrid(articles) {
    const container = document.getElementById('news-grid-container');
    if (!container) return;

    let html = '';
    articles.forEach(article => {
        const timeAgo = formatTimeAgo(article.published_at);
        const imageUrl = article.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=1170&q=80';
        const categoryName = article.category ? article.category.name : 'News';
        
        html += `
            <div class="news-card" data-id="${article.id}">
                <img src="${imageUrl}" alt="${article.title}">
                <div class="news-card-content">
                    <span class="news-category">${categoryName.toUpperCase()}</span>
                    <h3 class="news-title">${article.title}</h3>
                    <p class="news-excerpt">${article.description}</p>
                    <div class="news-meta">
                        <span><i class="far fa-clock"></i> ${timeAgo}</span>
                        <span><i class="far fa-eye"></i> ${article.views || 0} views</span>
                    </div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;

    // Attach click events
    container.querySelectorAll('.news-card').forEach(card => {
        card.addEventListener('click', () => {
            const id = card.dataset.id;
            window.location.href = `article.html?id=${id}`;
        });
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
        // Backend doesn't have article count out-of-the-box, so we leave it clean
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
        // Join messages with bullet
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

// ==================== Initialize Homepage ====================
async function initHomepage() {
    try {
        // Real API calls – Fetching parallel data from Django backend
        const [featuredRes, latestRes, trendingRes, breakingRes, categoriesRes] = await Promise.all([
            fetch(`${API_BASE_URL}/articles/?is_featured=true`),
            fetch(`${API_BASE_URL}/articles/`),
            fetch(`${API_BASE_URL}/articles/?is_trending=true`),
            fetch(`${API_BASE_URL}/articles/?is_breaking=true`),
            fetch(`${API_BASE_URL}/categories/`)
        ]);

        const featuredData = await featuredRes.json();
        const latestData = await latestRes.json();
        const trendingData = await trendingRes.json();
        const breakingData = await breakingRes.json();
        const categoriesData = await categoriesRes.json();

        // Render Featured (Take the first featured article)
        if (featuredData.results && featuredData.results.length > 0) {
            renderFeatured(featuredData.results[0]); 
        }

        // Render Grid (If container exists in HTML)
        renderGrid(latestData.results || []);

        // Render Trending Sidebar
        renderTrending(trendingData.results || []);

        // Render Categories Sidebar
        // If your DRF setup is paginated for categories it's categoriesData.results, else categoriesData
        renderCategories(categoriesData.results || categoriesData);

        // Render Breaking News Ticker (Extracting titles from breaking articles)
        const breakingTitles = (breakingData.results || []).map(item => item.title);
        renderBreakingTicker(breakingTitles);

    } catch (error) {
        console.error('Error fetching homepage data:', error);
    }
}

// Run when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize auth UI (if not already done in auth.js)
    if (typeof updateAuthUI === 'function') updateAuthUI();

    // Load homepage sections
    initHomepage();

    // Search form handling (if standalone search bar exists on homepage)
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-bar button');
    if (searchInput && searchButton) {
        searchButton.addEventListener('click', () => {
            const query = searchInput.value.trim();
            if (query) {
                window.location.href = `search.html?q=${encodeURIComponent(query)}`;
            }
        });
    }

    // Newsletter form
    const newsletterForm = document.getElementById('newsletterForm');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = newsletterForm.querySelector('input[type="email"]').value;
            const btn = newsletterForm.querySelector('button');
            
            btn.disabled = true;
            btn.textContent = 'Subscribing...';
            
            try {
                // Future Backend implementation space for newsletter
                // await fetch(`${CONFIG.API_BASE_URL}/newsletter/subscribe/`, { method: 'POST', body: JSON.stringify({email}), headers: {'Content-Type': 'application/json'} });
                
                alert(`Thank you for subscribing with: ${email}\nYou'll receive our newsletter shortly.`);
                newsletterForm.reset();
            } catch(err) {
                alert('Error subscribing. Please try again.');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Subscribe Now';
            }
        });
    }

    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navLinks = document.querySelector('.nav-links');
    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }
});