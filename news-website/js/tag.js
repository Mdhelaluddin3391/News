// js/tag.js
const TAG_API_URL = `${CONFIG.API_BASE_URL}/news/articles/`;
const TAGS_PER_PAGE = 6; // Naam change kar diya taaki script.js se clash na ho

function formatTagDate(isoString) {
    return new Date(isoString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Render HTML
function renderTagArticles(articles) {
    const tagArticlesContainer = document.getElementById('articles-container');
    if (!articles || articles.length === 0) {
        tagArticlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray); font-size: 1.1rem; grid-column: 1 / -1;">No articles found for this tag.</p>';
        return;
    }

    const user = getCurrentUser(); 
    const html = articles.map(article => {
        const imageUrl = article.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=300&q=80';
        const isSaved = user ? isArticleSaved(article.id) : false;
        const saveBtn = user ? `<button class="save-btn ${isSaved ? 'saved' : ''}" data-id="${article.id}">${isSaved ? 'Saved' : 'Save'}</button>` : '';

        // --- NAYA TRUNCATION LOGIC ---
        const rawDescription = article.description || '';
        const description = rawDescription.length > 110 
            ? rawDescription.substring(0, 110) + '...' 
            : rawDescription;
        // -----------------------------

        return `
            <div class="article-card">
                <img src="${imageUrl}" alt="${article.title}" class="article-image">
                <div class="article-content">
                    <h3 class="article-title">${article.title}</h3>
                    <p class="article-description">${description}</p>
                    <div class="article-meta">
                        <span class="article-source">${article.source_name || 'NewsHub'}</span>
                        <span class="article-date">${formatTagDate(article.published_at)}</span>
                        <a href="article.html?id=${article.id}" class="read-more">Read more →</a>
                        ${saveBtn}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    tagArticlesContainer.innerHTML = html;
}
// Fetch Logic
async function fetchTagResults(slug, page = 1) {
    const tagLoader = document.getElementById('loader');
    const tagErrorDiv = document.getElementById('error-message');
    const paginationBox = document.getElementById('pagination');

    tagLoader.style.display = 'block';
    tagErrorDiv.style.display = 'none';
    document.getElementById('articles-container').innerHTML = '';
    paginationBox.style.display = 'none';

    try {
        const url = new URL(TAG_API_URL);
        url.searchParams.append('tags__slug', slug); 
        url.searchParams.append('page', page);

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to load tag results");
        
        const data = await response.json();
        const results = data.results || data;
        
        renderTagArticles(results);
        
        if (data.count > TAGS_PER_PAGE) {
            setupTagPagination(page, data.count, slug);
            paginationBox.style.display = 'flex';
        }
        
    } catch (error) {
        tagErrorDiv.textContent = 'Network error. Please try again.';
        tagErrorDiv.style.display = 'block';
    } finally {
        tagLoader.style.display = 'none';
    }
}

// Pagination Logic
function setupTagPagination(currentPage, totalItems, slug) {
    const totalPages = Math.ceil(totalItems / TAGS_PER_PAGE);
    document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
    
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;

    prevBtn.onclick = () => {
        fetchTagResults(slug, currentPage - 1);
        window.scrollTo({top: 0, behavior: 'smooth'});
    };
    nextBtn.onclick = () => {
        fetchTagResults(slug, currentPage + 1);
        window.scrollTo({top: 0, behavior: 'smooth'});
    };
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const tagSlug = urlParams.get('slug');
    const tagName = urlParams.get('name');
    const tagHeading = document.getElementById('tag-heading');

    if (!tagSlug) {
        tagHeading.textContent = "Invalid Tag or No Tag Selected";
        return;
    }

    // Title ko update kar diya!
    tagHeading.innerHTML = `
    <i class="fas fa-tags tag-icon"></i> 
    Articles tagged with 
    <span class="highlight-tag">#${tagName || tagSlug}</span>
`;
    fetchTagResults(tagSlug, 1);
});