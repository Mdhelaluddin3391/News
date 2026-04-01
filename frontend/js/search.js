// js/search.js
// ==================== CONFIGURATION ====================
const SEARCH_API_BASE_URL = `${CONFIG.API_BASE_URL}/news/articles/`;
const SEARCH_ARTICLES_PER_PAGE = 6; // Isey aap 10 ya 12 bhi kar sakte hain industry standard ke hisaab se

// ==================== DOM Elements ====================
const searchHeading = document.getElementById('search-query') || document.getElementById('search-heading') || document.getElementById('search-query-heading');
const searchSubtitle = document.querySelector('.search-subtitle') || document.getElementById('search-subtitle');
const searchArticlesContainer = document.getElementById('articles-container');
const searchLoader = document.getElementById('loader');
const searchErrorDiv = document.getElementById('error-message');

// ==================== Helper Functions ====================
function showSearchLoader() { if (searchLoader) searchLoader.style.display = 'block'; }
function hideSearchLoader() { if (searchLoader) searchLoader.style.display = 'none'; }
function showSearchError(message) {
    if (searchErrorDiv) {
        searchErrorDiv.textContent = message;
        searchErrorDiv.style.display = 'block';
        setTimeout(() => { searchErrorDiv.style.display = 'none'; }, 5000);
    }
}
function clearSearchError() { if (searchErrorDiv) searchErrorDiv.style.display = 'none'; }
function formatSearchDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function renderSearchArticles(articles, query) {
    if (!searchArticlesContainer) return;

    if (!articles || articles.length === 0) {
        searchArticlesContainer.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; grid-column: 1 / -1; width: 100%;">
                <i class="fas fa-search-minus" style="font-size: 4rem; color: #ccc; margin-bottom: 20px;"></i>
                <h2 style="color: var(--dark); font-size: 1.8rem; margin-bottom: 10px;">No Results Found for "${query}"</h2>
                <p style="color: var(--gray); font-size: 1.1rem;">We couldn't find anything matching your search. Try checking your spelling or use more general terms (Tags, Categories, or Authors).</p>
            </div>
        `;
        return;
    }

    // Advanced Highlighter: Case-insensitive & wraps in mark tag
    const highlightText = (text, searchWord) => {
        if (!searchWord || !text) return text;
        const escapedWord = searchWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedWord})`, 'gi');
        return text.replace(regex, '<mark class="highlight-text" style="background-color: #ffeeba; color: #000; padding: 0 2px; border-radius: 3px;">$1</mark>');
    };

    const user = typeof getCurrentUser === 'function' ? getCurrentUser() : null;

    const html = articles.map(article => {
        const imageUrl = window.getFullImageUrl ? window.getFullImageUrl(article.featured_image, 'images/default-news.png') : 'images/default-news.png';
        const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
        
        const rawTitle = article.title || 'Untitled';
        
        // Smart Description: Agar content mein match hai, toh wo hissa dikhao
        let rawDescription = article.description || '';
        if(!rawDescription && article.content) {
             rawDescription = article.content.replace(/<[^>]*>?/gm, '').substring(0, 150); // Fallback to content snippet
        }
        
        const shortDesc = rawDescription.length > 120 ? rawDescription.substring(0, 120) + '...' : rawDescription;
        
        const title = highlightText(rawTitle, query);
        const description = highlightText(shortDesc, query);
        
        const source = article.category ? article.category.name : 'News';
        const date = article.published_at ? formatSearchDate(article.published_at) : 'Unknown date';
        const articleId = article.id || '';
        const isSaved = user && typeof isArticleSaved === 'function' ? isArticleSaved(articleId) : false;
        
        const saveButton = user ? 
            `<button class="save-btn ${isSaved ? 'saved' : ''}" data-id="${articleId}">
                <i class="fa${isSaved ? 's' : 'r'} fa-bookmark"></i> ${isSaved ? 'Saved' : 'Save'}
            </button>` : '';

        // Added Tags Display in Search Results
        const tagsHtml = (article.tags && article.tags.length > 0) 
            ? `<div class="search-tags" style="margin-top: 10px; font-size: 0.8rem;">
                 ${article.tags.slice(0, 3).map(tag => `<span style="background: #f1f1f1; padding: 2px 8px; border-radius: 12px; margin-right: 5px; color: #555;">#${highlightText(tag.name, query)}</span>`).join('')}
               </div>` 
            : '';

        return `
            <div class="article-card" style="display: flex; flex-direction: column; height: 100%;">
                <img src="${imageUrl}" alt="${rawTitle}" class="article-image ${containClass}" loading="lazy" style="height: 200px; object-fit: cover;">
                <div class="article-content" style="flex: 1; display: flex; flex-direction: column;">
                    <span class="article-source" style="font-size: 0.8rem; color: var(--primary); text-transform: uppercase; font-weight: bold; margin-bottom: 5px;">${highlightText(source, query)}</span>
                    <h3 class="article-title" style="margin-bottom: 10px;">${title}</h3>
                    <p class="article-description" style="flex: 1;">${description}</p>
                    ${tagsHtml}
                    <div class="article-meta" style="margin-top: 15px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #eee; padding-top: 10px;">
                        <span class="article-date"><i class="far fa-clock"></i> ${date}</span>
                        <a href="/article.html?slug=${article.slug}" class="read-more" style="font-weight: 600;">Read more →</a>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    searchArticlesContainer.innerHTML = html;

    // Attach Save Listeners
    if (user) {
        document.querySelectorAll('.save-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const articleId = btn.dataset.id;
                const article = articles.find(a => a.id == articleId);
                if (!article) return;

                if (btn.classList.contains('saved')) {
                    if(typeof unsaveArticle === 'function') unsaveArticle(articleId);
                    btn.classList.remove('saved');
                    btn.innerHTML = '<i class="far fa-bookmark"></i> Save';
                    if(typeof showToast === 'function') showToast('Removed from saved articles', 'info');
                } else {
                    if(typeof saveArticle === 'function') saveArticle(article);
                    btn.classList.add('saved');
                    btn.innerHTML = '<i class="fas fa-bookmark"></i> Saved';
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
        url.searchParams.append('search', query); 
        url.searchParams.append('page', page);

        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        
        const data = await response.json();
        const results = data.results || data; 
        const totalResults = data.count || results.length;

        renderSearchArticles(results, query);
        updateSearchPagination(page, totalResults, query);
        
        if (searchHeading) {
            searchHeading.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-search" style="color: var(--primary);"></i> 
                    <span>Found <strong>${totalResults}</strong> results for <span class="highlight-search" style="color: var(--primary);">"${query}"</span></span>
                </div>
            `;
        }

        if (searchSubtitle) searchSubtitle.style.display = 'none';

        if (typeof updateSEOMetaTags === 'function') {
            updateSEOMetaTags(
                `"${query}" - Search Results | Ferox Times`, 
                `Explore news articles, authors, tags and stories related to "${query}" on Ferox Times.`, 
                'images/default-news.png', 
                window.location.href,
                `${query} news, search ${query}, Ferox Times results, trending ${query}`
            );
        }
        
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

    if(totalPages > 1) {
        if(paginationBox) paginationBox.style.display = 'flex';
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;

        prevBtn.disabled = currentPage <= 1;
        nextBtn.disabled = currentPage >= totalPages;

        prevBtn.replaceWith(prevBtn.cloneNode(true));
        nextBtn.replaceWith(nextBtn.cloneNode(true));

        document.getElementById('prev-page').addEventListener('click', () => {
            if (currentPage > 1) {
                fetchSearchResults(query, currentPage - 1);
                updateURL(query, currentPage - 1);
            }
        });

        document.getElementById('next-page').addEventListener('click', () => {
            if (currentPage < totalPages) {
                fetchSearchResults(query, currentPage + 1);
                updateURL(query, currentPage + 1);
            }
        });
    } else {
        if(paginationBox) paginationBox.style.display = 'none';
    }
}

function updateURL(query, page) {
    const url = new URL(window.location);
    url.searchParams.set('q', query);
    url.searchParams.set('page', page);
    window.history.pushState({}, '', url);
    window.scrollTo({top: 0, behavior: 'smooth'});
}

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('/search')) return; 

    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q') || urlParams.get('search') || '';
    const page = parseInt(urlParams.get('page')) || 1;

    if (typeof loadEditorsPicks === 'function') loadEditorsPicks();
    if (typeof loadTrendingNews === 'function') loadTrendingNews();
    if (typeof loadCategoriesSidebar === 'function') loadCategoriesSidebar();

    const searchInput = document.querySelector('input[name="q"]') || document.querySelector('#header-search-input');
    if (searchInput) searchInput.value = query;

    if (!query) {
        if (searchHeading) searchHeading.textContent = 'Search News & Articles';
        if (searchArticlesContainer) {
            searchArticlesContainer.innerHTML = `
                <div style="text-align: center; padding: 60px; grid-column: 1/-1;">
                    <i class="fas fa-keyboard" style="font-size: 3rem; color: #ccc; margin-bottom: 15px;"></i>
                    <h3>What are you looking for?</h3>
                    <p style="color: gray;">Search for tags, topics, authors, or specific keywords.</p>
                </div>`;
        }
        return;
    }

    fetchSearchResults(query, page);
});