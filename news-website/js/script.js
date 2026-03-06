// js/script.js
// ==================== CONFIGURATION ====================
// Real Django API Endpoint
const API_BASE_URL = `${CONFIG.API_BASE_URL}/news`;
const DEFAULT_CATEGORY = 'general';
const ARTICLES_PER_PAGE = 6;

// ==================== DOM Elements ====================
const categoryHeading = document.getElementById('category-heading');
const articlesContainer = document.getElementById('articles-container');
const loader = document.getElementById('loader');
const errorMessageDiv = document.getElementById('error-message');
const categoryButtons = document.querySelectorAll('.category-btn');

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

// ==================== Rendering ====================
function renderArticles(articles) {
    if (!articles || articles.length === 0) {
        articlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray);">No articles found.</p>';
        return;
    }

    const user = getCurrentUser(); // from auth.js
    const html = articles.map(article => {
        // Map backend fields
        const imageUrl = article.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
        const title = article.title || 'Untitled';
        const description = article.description || 'No description available.';
        const source = article.source_name || 'NewsHub';
        const date = article.published_at ? formatDate(article.published_at) : 'Unknown date';
        const articleId = article.id || '';
        
        const isSaved = user ? isArticleSaved(articleId) : false;
        const saveButton = user ?
            `<button class="save-btn ${isSaved ? 'saved' : ''}" data-id="${articleId}">${isSaved ? 'Saved' : 'Save'}</button>`
            : '';

        return `
            <div class="article-card">
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
                } else {
                    saveArticle(article);
                    btn.classList.add('saved');
                    btn.textContent = 'Saved';
                }
            });
        });
    }
}

// ==================== Fetch News ====================
async function fetchNews(category = DEFAULT_CATEGORY, page = 1) {
    showLoader();
    clearError();
    articlesContainer.innerHTML = '';

    try {
        // Construct API URL with category filter and pagination
        const url = new URL(`${API_BASE_URL}/articles/`);
        // We use category__slug to filter via DRF
        url.searchParams.append('category__slug', category); 
        url.searchParams.append('page', page);

        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        
        const data = await response.json();
        
        // DRF returns paginated data in 'results', total count in 'count'
        const articles = data.results || data;
        const totalResults = data.count || articles.length;

        renderArticles(articles);
        updatePagination(page, totalResults, category);
        
        if(categoryHeading) {
            categoryHeading.textContent = category.charAt(0).toUpperCase() + category.slice(1) + ' News';
        }
        
    } catch (error) {
        console.error('Fetch failed:', error);
        showError('Failed to load news. Please try again later.');
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

// ==================== App Initialization ====================
document.addEventListener('DOMContentLoaded', () => {
    // Check if we are on a page that needs to fetch the grid (like category page)
    if(articlesContainer) {
        const urlParams = new URLSearchParams(window.location.search);
        const category = urlParams.get('category') || DEFAULT_CATEGORY;
        const page = parseInt(urlParams.get('page')) || 1;
        
        setActiveCategory(category);
        fetchNews(category, page);
    }
});