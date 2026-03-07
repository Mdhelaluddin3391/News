// js/search.js
// ==================== CONFIGURATION ====================
// Real API Endpoint pointing to your Django backend's articles endpoint
const SEARCH_API_BASE_URL = `${CONFIG.API_BASE_URL}/news/articles/`;
const SEARCH_ARTICLES_PER_PAGE = 6;

// ==================== DOM Elements ====================
const searchHeading = document.getElementById('search-query-heading');
const searchArticlesContainer = document.getElementById('articles-container');
const searchLoader = document.getElementById('loader');
const searchErrorDiv = document.getElementById('error-message');

// ==================== Helper Functions ====================
function showSearchLoader() {
    searchLoader.style.display = 'block';
}

function hideSearchLoader() {
    searchLoader.style.display = 'none';
}

function showSearchError(message) {
    searchErrorDiv.textContent = message;
    searchErrorDiv.style.display = 'block';
    setTimeout(() => {
        searchErrorDiv.style.display = 'none';
    }, 5000);
}

function clearSearchError() {
    searchErrorDiv.style.display = 'none';
}

function formatSearchDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

// ==================== Rendering ====================
function renderSearchArticles(articles) {
    if (!articles || articles.length === 0) {
        searchArticlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray);">No articles found matching your query.</p>';
        return;
    }

    const user = getCurrentUser(); // from auth.js
    const html = articles.map(article => {
        // Map backend fields
        const imageUrl = article.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
        const title = article.title || 'Untitled';
        const description = article.description || 'No description available.';
        const source = article.source_name || 'NewsHub';
        const date = article.published_at ? formatSearchDate(article.published_at) : 'Unknown date';
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

    searchArticlesContainer.innerHTML = html;

    // Attach event listeners to save buttons if user is logged in
    if (user) {
        document.querySelectorAll('.save-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const articleId = btn.dataset.id;
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

// ==================== Fetch Search Results ====================
async function fetchSearchResults(query, page = 1) {
    showSearchLoader();
    clearSearchError();
    searchArticlesContainer.innerHTML = '';

    try {
        const url = new URL(SEARCH_API_BASE_URL);
        // Django Rest Framework SearchFilter default parameter is 'search'
        url.searchParams.append('search', query); 
        url.searchParams.append('page', page);

        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        
        const data = await response.json();
        const results = data.results || data; // Handle paginated DRF response
        const totalResults = data.count || results.length;

        renderSearchArticles(results);
        updateSearchPagination(page, totalResults, query);
        searchHeading.textContent = `Search Results for "${query}"`;
        
    } catch (error) {
        console.error('Search failed:', error);
        showSearchError('Could not complete search. Please try again later.');
    } finally {
        hideSearchLoader();
    }
}

// ==================== Pagination ====================
function updateSearchPagination(currentPage, totalItems, query) {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const pageInfo = document.getElementById('page-info');

    if (!prevBtn || !nextBtn || !pageInfo) return;

    const totalPages = Math.ceil(totalItems / SEARCH_ARTICLES_PER_PAGE) || 1;

    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;

    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;

    // Remove old listeners and add new ones
    prevBtn.replaceWith(prevBtn.cloneNode(true));
    nextBtn.replaceWith(nextBtn.cloneNode(true));

    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            fetchSearchResults(query, currentPage - 1);
            const url = new URL(window.location);
            url.searchParams.set('page', currentPage - 1);
            window.history.pushState({}, '', url);
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        if (currentPage < totalPages) {
            fetchSearchResults(query, currentPage + 1);
            const url = new URL(window.location);
            url.searchParams.set('page', currentPage + 1);
            window.history.pushState({}, '', url);
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    });
}

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q') || '';
    const page = parseInt(urlParams.get('page')) || 1;

    // Populate search input in the header if it exists
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.value = query;
    }

    if (!query) {
        searchHeading.textContent = 'Search Results';
        searchArticlesContainer.innerHTML = '<p style="text-align: center;">Enter a search term above.</p>';
        return;
    }

    fetchSearchResults(query, page);
});