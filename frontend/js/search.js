// js/search.js
// ==================== CONFIGURATION ====================
// Real API Endpoint pointing to your Django backend's articles endpoint
const SEARCH_API_BASE_URL = `${CONFIG.API_BASE_URL}/news/articles/`;
const SEARCH_ARTICLES_PER_PAGE = 6;

// ==================== DOM Elements ====================
// NAYA: Fallback IDs add kiye hain taaki agar ek ID na mile toh dusri try kare aur code crash na ho
const searchHeading = document.getElementById('search-query') || document.getElementById('search-heading') || document.getElementById('search-query-heading');
const searchSubtitle = document.querySelector('.search-subtitle') || document.getElementById('search-subtitle');
const searchArticlesContainer = document.getElementById('articles-container');
const searchLoader = document.getElementById('loader');
const searchErrorDiv = document.getElementById('error-message');

// ==================== Helper Functions ====================
function showSearchLoader() {
    if (searchLoader) searchLoader.style.display = 'block';
}

function hideSearchLoader() {
    if (searchLoader) searchLoader.style.display = 'none';
}

function showSearchError(message) {
    if (searchErrorDiv) {
        searchErrorDiv.textContent = message;
        searchErrorDiv.style.display = 'block';
        setTimeout(() => {
            searchErrorDiv.style.display = 'none';
        }, 5000);
    }
}

function clearSearchError() {
    if (searchErrorDiv) searchErrorDiv.style.display = 'none';
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
function renderSearchArticles(articles, query) {
    if (!searchArticlesContainer) return; // Safety check

    if (!articles || articles.length === 0) {
        // Better "No Results" UI with Icon
        searchArticlesContainer.innerHTML = `
            <div style="text-align: center; padding: 50px 20px; grid-column: 1 / -1;">
                <i class="fas fa-search" style="font-size: 3rem; color: var(--border); margin-bottom: 20px;"></i>
                <h3 style="color: var(--dark);">No articles found</h3>
                <p style="color: var(--gray);">Try different keywords or check your spelling.</p>
            </div>
        `;
        return;
    }

    // Helper function to highlight keywords in text
    const highlightText = (text, searchWord) => {
        if (!searchWord || !text) return text;
        // Escape special characters to prevent regex errors
        const escapedWord = searchWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedWord})`, 'gi');
        return text.replace(regex, '<span class="highlight-text">$1</span>');
    };

    const user = typeof getCurrentUser === 'function' ? getCurrentUser() : null; // from auth.js
    const html = articles.map(article => {
        // Map backend fields
        // NAYA CODE: Global helper function use kiya gaya image URL ke liye
        const imageUrl = window.getFullImageUrl(article.featured_image, 'images/default-news.png');
        const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
        
        // Fetch Title & Description and apply Truncation and Highlighting
        const rawTitle = article.title || 'Untitled';
        const rawDescription = article.description || '';
        const shortDesc = rawDescription.length > 110 ? rawDescription.substring(0, 110) + '...' : rawDescription;
        
        const title = highlightText(rawTitle, query);
        const description = highlightText(shortDesc, query);
        
        const source = article.source_name || 'Ferox Times';
        const date = article.published_at ? formatSearchDate(article.published_at) : 'Unknown date';
        const articleId = article.id || '';
        const isSaved = user && typeof isArticleSaved === 'function' ? isArticleSaved(articleId) : false;
        
        const saveButton = user ? 
            `<button class="save-btn ${isSaved ? 'saved' : ''}" data-id="${articleId}">${isSaved ? 'Saved' : 'Save'}</button>` 
            : '';

        return `
            <div class="article-card">
                <img src="${imageUrl}" alt="${rawTitle}" class="article-image ${containClass}" loading="lazy">
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
                    if(typeof unsaveArticle === 'function') unsaveArticle(articleId);
                    btn.classList.remove('saved');
                    btn.textContent = 'Save';
                    if(typeof showToast === 'function') showToast('Removed from saved articles', 'info');
                } else {
                    if(typeof saveArticle === 'function') saveArticle(article);
                    btn.classList.add('saved');
                    btn.textContent = 'Saved';
                    if(typeof showToast === 'function') showToast('Article saved successfully!', 'success');
                }
            });
        });
    }
}

// ==================== Fetch Search Results ====================
async function fetchSearchResults(query, page = 1) {
    showSearchLoader();
    clearSearchError();
    if (searchArticlesContainer) searchArticlesContainer.innerHTML = '';

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

        renderSearchArticles(results, query);
        updateSearchPagination(page, totalResults, query);
        
        // NAYA: Yahan null check laga diya hai taaki TypeError na aaye
        if (searchHeading) {
            searchHeading.innerHTML = `
                <i class="fas fa-search" style="font-size: 1rem; color: var(--primary); opacity: 0.7;"></i> 
                Results for <span class="highlight-search">${query}</span>
            `;
        }

        if (searchSubtitle) {
            searchSubtitle.style.display = 'none';
        }

        // Search Page SEO Update
        if (typeof updateSEOMetaTags === 'function') {
            updateSEOMetaTags(
                `"${query}" - Search Results | Ferox Times`, 
                `Explore news articles and stories related to "${query}" on Ferox Times. Find the most relevant updates.`, 
                'images/default-news.png', 
                window.location.href,
                `${query} news, search ${query}, Ferox Times results` // <-- NAYA: Keywords
            );
        }

        // Optional: Count display
        const countDiv = document.getElementById('results-count');
        if (countDiv) countDiv.textContent = `Found ${totalResults} articles matching your query`;
        
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
    const paginationBox = document.getElementById('pagination');

    if (!prevBtn || !nextBtn || !pageInfo) return;

    const totalPages = Math.ceil(totalItems / SEARCH_ARTICLES_PER_PAGE) || 1;

    // Sirf tabhi pagination dikhao jab 1 se zyada page hon
    if(totalPages > 1) {
        if(paginationBox) paginationBox.style.display = 'flex';
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
    } else {
        if(paginationBox) paginationBox.style.display = 'none';
    }
}

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', () => {
    // FIX: Check if we are currently on the search page. 
    // If we are NOT on the search page, stop executing this script.
    if (!window.location.pathname.includes('search.html')) {
        return; 
    }

    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q') || urlParams.get('search') || '';
    const page = parseInt(urlParams.get('page')) || 1;

    // Sidebar Data Load karein (Global functions from homepage.js)
    if (typeof loadEditorsPicks === 'function') loadEditorsPicks();
    if (typeof loadTrendingNews === 'function') loadTrendingNews();
    if (typeof loadCategoriesSidebar === 'function') loadCategoriesSidebar();

    // Populate search input in the header if it exists
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.value = query;
    }

    if (!query) {
        // Null check added here
        if (searchHeading) {
            searchHeading.textContent = 'Search Results';
        }
        if (searchArticlesContainer) {
            searchArticlesContainer.innerHTML = '<p style="text-align: center; margin-top: 50px;">Please enter a search term to find articles.</p>';
        }
        
        if (typeof updateSEOMetaTags === 'function') {
            updateSEOMetaTags(
                `Search News - Ferox Times`, 
                `Search our database for the latest news articles and stories on Ferox Times.`, 
                'images/default-news.png', 
                window.location.href
            );
        }
        return;
    }

    fetchSearchResults(query, page);
});