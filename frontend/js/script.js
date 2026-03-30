// js/script.js
// ==================== CONFIGURATION ====================
// Real Django API Endpoint
const NEWS_API_URL = `${window.APP_CONFIG.API_BASE_URL}/news`;
const DEFAULT_CATEGORY = 'general';
const ARTICLES_PER_PAGE = 6;

// ==================== DOM Elements ====================
const categoryHeading = document.getElementById('category-heading');
const articlesContainer = document.getElementById('articles-container');
const loader = document.getElementById('loader');
const errorMessageDiv = document.getElementById('error-message');
const categoryButtons = document.querySelectorAll('.category-btn');

// ==================== GLOBAL HELPER FUNCTION (For Images) ====================
window.getFullImageUrl = function(imagePath, fallbackImage = 'images/default-news.png') {
    if (!imagePath) return fallbackImage;

    // Handle absolute URLs (from backend)
    if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
        // Since we're using Nginx gateway, convert backend URLs to relative paths
        try {
            const url = new URL(imagePath);
            if (url.pathname.startsWith('/media/')) {
                return url.pathname; // Use relative path for media files
            }
        } catch (e) {
            // Invalid URL, return as is
        }
        return imagePath;
    }

    // Handle relative paths
    if (imagePath.startsWith('/')) {
        return imagePath;
    }

    // Return as is for other cases
    return imagePath;
};

// ==================== Helper Functions ====================
function showLoader() { loader.style.display = 'block'; }
function hideLoader() { loader.style.display = 'none'; }

function showError(message) {
    errorMessageDiv.textContent = message;
    errorMessageDiv.style.display = 'block';
    setTimeout(() => { errorMessageDiv.style.display = 'none'; }, 5000);
}

function clearError() { errorMessageDiv.style.display = 'none'; }

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

async function normalizeApiPayload(payload) {
    if (payload instanceof Response) {
        if (!payload.ok) {
            const text = await payload.text();
            throw new Error(`API error ${payload.status}: ${text}`);
        }

        return payload.json();
    }

    return payload;
}

// ==================== Rendering ====================
function renderArticles(articles) {
    // FIX: Check karein ki articles sach mein ek array hai ya nahi
    if (!articles || !Array.isArray(articles) || articles.length === 0) {
        if (articlesContainer) {
            // 'grid-column: 1 / -1' isliye takki ye message center mein aaye
            articlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray); grid-column: 1 / -1; padding: 2rem;">No articles found in this category.</p>';
        }
        return;
    }

    const user = getCurrentUser(); // from auth.js
    const html = articles.map(article => {
        // NAYA CODE: Yahan global helper use kiya gaya hai production-ready image URL ke liye
        const imageUrl = window.getFullImageUrl(article.featured_image, 'images/default-news.png');
        
        const title = article.title || 'Untitled';
        const description = article.description ? (article.description.length > 110 ? article.description.substring(0, 110) + '...' : article.description) : 'No description available.';
        const source = article.source_name || 'Forex Times';
        const date = article.published_at ? formatDate(article.published_at) : 'Unknown date';
        const articleId = article.id || '';
        
        const isSaved = user ? isArticleSaved(articleId) : false;
        const saveButton = user ?
            `<button class="save-btn ${isSaved ? 'saved' : ''}" data-id="${articleId}">${isSaved ? 'Saved' : 'Save'}</button>`
            : '';

        const liveBadgeHTML = article.is_live ? `<div class="live-badge-card"><i class="fas fa-circle"></i> LIVE</div>` : '';

        return `
            <div class="article-card" style="position: relative;">
                ${liveBadgeHTML}
                <img src="${imageUrl}" alt="${title}" class="article-image" loading="lazy">
                <div class="article-content">
                    <h3 class="article-title">${title}</h3>
                    <p class="article-description">${description}</p>
                    <div class="article-meta">
                        <span class="article-source">${source}</span>
                        <span class="article-date">${date}</span>
                        <a href="article.html?id=${articleId}" class="read-more">Read more →</a>
                        ${saveButton}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    articlesContainer.innerHTML = html;

    // Attach event listeners to save buttons if user logged in
    if (user) {
        document.querySelectorAll('.save-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const articleId = btn.dataset.id;
                // Find full article from rendered list
                const article = articles.find(a => a.id == articleId);
                if (!article) return;

                if (btn.classList.contains('saved')) {
                    unsaveArticle(articleId);
                    btn.classList.remove('saved');
                    btn.textContent = 'Save';
                    showToast('Removed from saved articles', 'info'); 
                } else {
                    saveArticle(article);
                    btn.classList.add('saved');
                    btn.textContent = 'Saved';
                    showToast('Article saved successfully!', 'success'); 
                }
            });
        });
    }
}

// ==================== Fetch News ====================
async function fetchNews(category = DEFAULT_CATEGORY, page = 1) {
    showLoader();
    clearError();
    if (articlesContainer) articlesContainer.innerHTML = '';

    try {
        const cleanCategory = category.toLowerCase();
        
        // NAYA CODE: Use standard fetch with NEWS_API_URL to match homepage.js exactly
        const response = await fetch(`${NEWS_API_URL}/articles/?category__slug=${encodeURIComponent(cleanCategory)}&page=${encodeURIComponent(page)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        let articles = [];
        let totalResults = 0;

        if (data && Array.isArray(data.results)) {
            articles = data.results;
            totalResults = data.count || articles.length;
        } else if (Array.isArray(data)) {
            articles = data;
            totalResults = articles.length;
        }

        renderArticles(articles);
        updatePagination(page, totalResults, category);
        
        if(categoryHeading) {
            const formattedCategoryName = category.charAt(0).toUpperCase() + category.slice(1);
            categoryHeading.textContent = formattedCategoryName + ' News';
            
            if (typeof updateSEOMetaTags === 'function') {
                updateSEOMetaTags(
                    `${formattedCategoryName} News`, 
                    `Read the latest breaking news about ${formattedCategoryName} on Forex Times.`, 
                    'images/default-news.png',
                    window.location.href
                );
            }
        }
        
    } catch (error) {
        console.error('Fetch failed:', error);
        showError('Failed to load news. Please try again later.');
        renderArticles([]); 
    } finally {
        hideLoader();
    }
}

// ==================== Pagination Logic ====================
function updatePagination(currentPage, totalItems, category) {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const pageInfo = document.getElementById('page-info');

    if (!prevBtn || !nextBtn || !pageInfo) return;

    const totalPages = Math.ceil(totalItems / ARTICLES_PER_PAGE) || 1;

    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;

    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;

    // Remove old listeners and add new ones
    prevBtn.replaceWith(prevBtn.cloneNode(true));
    nextBtn.replaceWith(nextBtn.cloneNode(true));

    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            fetchNews(category, currentPage - 1);
            // Update URL without reload
            const url = new URL(window.location);
            url.searchParams.set('page', currentPage - 1);
            window.history.pushState({}, '', url);
            
            // Scroll top
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        if (currentPage < totalPages) {
            fetchNews(category, currentPage + 1);
            const url = new URL(window.location);
            url.searchParams.set('page', currentPage + 1);
            window.history.pushState({}, '', url);
            
            // Scroll top
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    });
}

// ==================== Category Switching ====================
function setActiveCategory(category) {
    if(categoryButtons.length === 0) return;
    
    categoryButtons.forEach(btn => {
        const btnCategory = btn.getAttribute('data-category');
        if (btnCategory === category) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

if(categoryButtons) {
    categoryButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const category = e.target.getAttribute('data-category');
            setActiveCategory(category);
            fetchNews(category, 1);
            
            // Update URL: remove page param, set category
            const url = new URL(window.location);
            url.searchParams.set('category', category);
            url.searchParams.delete('page');
            window.history.pushState({}, '', url);
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const homeContainer = document.getElementById('home-categories-container');
    
    if(articlesContainer) {
        const urlParams = new URLSearchParams(window.location.search);
        const category = urlParams.get('category') || DEFAULT_CATEGORY;
        const page = parseInt(urlParams.get('page')) || 1;
        
        setActiveCategory(category);

        // --- GLOBAL SIDEBAR DATA (Har page ke liye) ---
        // Yeh functions homepage.js mein hain, inhein yahan bahar call karein
        if (typeof loadTopStories === 'function') loadTopStories();
        if (typeof loadEditorsPicks === 'function') loadEditorsPicks();
        if (typeof loadTrendingNews === 'function') loadTrendingNews();
        if (typeof loadCategoriesSidebar === 'function') loadCategoriesSidebar();
        if (typeof loadBreakingNews === 'function') loadBreakingNews();
        // ----------------------------------------------

        const paginationContainer = document.getElementById('pagination');
        const featuredSection = document.querySelector('.featured-news'); 
        const webStoriesSection = document.querySelector('.web-stories-section'); // <-- NAYA
        const recentNewsSection = document.getElementById('recent-news-section'); // <-- NAYA
        
        if (category === 'general' && homeContainer) {
            // Homepage logic
            articlesContainer.style.display = 'none';
            if(paginationContainer) paginationContainer.style.display = 'none';
            if(categoryHeading) categoryHeading.style.display = 'none';
            if(homeContainer) homeContainer.style.display = 'block';
            if(featuredSection) featuredSection.style.display = 'block'; 
            if(webStoriesSection) webStoriesSection.style.display = 'block'; // <-- NAYA
            
            if (typeof initHomepage === 'function') {
                initHomepage();
            }
        } else { 
            // Category Page logic
            articlesContainer.style.display = 'grid'; 
            if(paginationContainer) paginationContainer.style.display = 'flex';
            if(categoryHeading) categoryHeading.style.display = 'block';
            if(homeContainer) homeContainer.style.display = 'none';
            if(featuredSection) featuredSection.style.display = 'none'; 
            if(webStoriesSection) webStoriesSection.style.display = 'none'; // <-- NAYA (Hide on category)
            if(recentNewsSection) recentNewsSection.style.display = 'none'; // <-- NAYA (Hide on category)
            
            fetchNews(category, page);
        }
    }
});

// ==================== TOAST NOTIFICATION SYSTEM ====================
function showToast(message, type = 'success') {
    // Check agar container pehle se hai, nahi toh banao
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    // Naya toast element banao
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Icon set karein type ke hisaab se
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';

    // FIX: icon aur toast-icon ke beech space diya gaya hai
    toast.innerHTML = `<i class="fas ${icon} toast-icon" style="font-size: 1.2rem;"></i> <span>${message}</span>`;
    container.appendChild(toast);

    // Slide In animation
    setTimeout(() => toast.classList.add('show'), 10);

    // 3 second baad Slide Out aur remove kar do
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400); // Animation khatam hone ka wait
    }, 3000);
}



/// ==================== SEO META TAGS & CANONICAL UPDATER ====================
function updateSEOMetaTags(title, description, imageUrl, pageUrl, keywords = "") {
    // 1. Page ka Title update karein
    document.title = title ? `${title} - Forex Times` : 'Forex Times - Premium News';

    // Helper function: Agar tag pehle se hai toh update karein, nahi toh naya banayein
    function setMetaTag(attrName, attrValue, content) {
        if (!content) return; 
        let element = document.querySelector(`meta[${attrName}="${attrValue}"]`);
        if (!element) {
            element = document.createElement('meta');
            element.setAttribute(attrName, attrValue);
            document.head.appendChild(element);
        }
        element.setAttribute('content', content);
    }

    // 2. Standard SEO Description & Keywords
    setMetaTag('name', 'description', description);
    if (keywords) {
        setMetaTag('name', 'keywords', keywords);
    }

    // 3. Open Graph Tags
    setMetaTag('property', 'og:title', title);
    setMetaTag('property', 'og:description', description);
    setMetaTag('property', 'og:image', imageUrl);
    setMetaTag('property', 'og:url', pageUrl);
    setMetaTag('property', 'og:type', 'article');
    setMetaTag('property', 'og:site_name', 'Forex Times');

    // 4. Twitter Card Tags
    setMetaTag('name', 'twitter:card', 'summary_large_image');
    setMetaTag('name', 'twitter:title', title);
    setMetaTag('name', 'twitter:description', description);
    setMetaTag('name', 'twitter:image', imageUrl);

    // 5. Canonical URL Handle (Taaki duplicate content ki penalty na lage)
    let canonicalTag = document.querySelector('link[rel="canonical"]');
    if (!canonicalTag) {
        canonicalTag = document.createElement('link');
        canonicalTag.setAttribute('rel', 'canonical');
        document.head.appendChild(canonicalTag);
    }
    // URL se extra parameters ya hash hata kar clean canonical link set karein
    const cleanUrl = pageUrl.split('#')[0]; 
    canonicalTag.setAttribute('href', cleanUrl);
}


// ==================== SCHEMA MARKUP (JSON-LD) INJECTOR ====================
function injectSchema(schemaData) {
    const existingSchema = document.getElementById('dynamic-schema');
    if (existingSchema) {
        existingSchema.remove();
    }

    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.id = 'dynamic-schema';
    
    // Agar array of schemas (jaise Article + Breadcrumb) pass kiya gaya hai, toh @graph banayenge
    if (Array.isArray(schemaData)) {
        const graphSchema = {
            "@context": "https://schema.org",
            "@graph": schemaData
        };
        script.text = JSON.stringify(graphSchema);
    } else {
        script.text = JSON.stringify(schemaData);
    }
    
    document.head.appendChild(script);
}
