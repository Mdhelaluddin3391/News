// js/tag.js
const TAG_API_URL = `${CONFIG.API_BASE_URL}/news/articles/`;
const TAGS_PER_PAGE = 12; // Naam change kar diya taaki script.js se clash na ho

function formatTagDate(isoString) {
    return new Date(isoString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function renderTagArticles(articles) {
    const tagArticlesContainer = document.getElementById('articles-container');
    if (!articles || articles.length === 0) {
        tagArticlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray); font-size: 1.1rem; grid-column: 1 / -1;">No articles found for this tag.</p>';
        return;
    }

    const user = getCurrentUser(); 
    const html = articles.map(article => {
        const imageUrl = window.getFullImageUrl(article.featured_image, '/images/default-news.png');
        const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
        const safeTitle = typeof window.escapeHtml === 'function' ? window.escapeHtml(article.title || 'Untitled') : (article.title || 'Untitled');
        
        const isSaved = user ? isArticleSaved(article.id) : false;
        const saveBtn = user ? `<button class="save-btn ${isSaved ? 'saved' : ''}" data-id="${article.id}">${isSaved ? 'Saved' : 'Save'}</button>` : '';

        const rawDescription = article.description || '';
        const description = rawDescription.length > 110 
            ? rawDescription.substring(0, 110) + '...' 
            : rawDescription;
        const safeDescription = typeof window.escapeHtml === 'function' ? window.escapeHtml(description) : description;
        const safeSource = typeof window.escapeHtml === 'function'
            ? window.escapeHtml(article.source_name || 'Ferox Times')
            : (article.source_name || 'Ferox Times');

        // ✅ SEO FIX: Use clean URL for article links
        return `
            <div class="article-card">
                <img src="${imageUrl}" alt="${safeTitle}" class="article-image ${containClass}">
                <div class="article-content">
                    <h3 class="article-title">${safeTitle}</h3>
                    <p class="article-description">${safeDescription}</p>
                    <div class="article-meta">
                        <span class="article-source">${safeSource}</span>
                        <span class="article-date">${formatTagDate(article.published_at)}</span>
                        <a href="/article/${article.slug}" class="read-more">Read more →</a>
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
    // ✅ SEO FIX: Support reading tag from Clean URL path (e.g. /tag/technology)
    const pathParts = window.location.pathname.split('/').filter(Boolean);
    const urlParams = new URLSearchParams(window.location.search);
    
    let tagSlug = urlParams.get('slug');
    let tagName = urlParams.get('name');
    
    // If no query params, check the path
    if (!tagSlug && pathParts.length >= 2 && pathParts[0] === 'tag') {
        tagSlug = pathParts[1];
        // Create a display-friendly name from the slug if no name is provided
        tagName = tagName || tagSlug.charAt(0).toUpperCase() + tagSlug.slice(1).replace(/-/g, ' ');
    }

    const tagHeading = document.getElementById('tag-heading');

    if (!tagSlug) {
        tagHeading.textContent = "Invalid Tag or No Tag Selected";
        
        if (typeof updateSEOMetaTags === 'function') {
            updateSEOMetaTags(
                `Tags - Ferox Times`, 
                `Browse our collection of news articles by topics and tags on Ferox Times.`, 
                '/images/default-news.png', 
                window.location.origin + '/tag/'
            );
        }
        return;
    }

    const displayTagName = tagName || tagSlug;
    const safeDisplayTagName = typeof window.escapeHtml === 'function' ? window.escapeHtml(displayTagName) : displayTagName;

    tagHeading.innerHTML = `
    <i class="fas fa-tags tag-icon"></i> 
    Articles tagged with 
    <span class="highlight-tag">#${safeDisplayTagName}</span>
    `;

    // ✅ SEO FIX: Use clean URL for tag specific canonical and meta tags
    const cleanTagUrl = `${window.location.origin}/tag/${tagSlug}`;

    if (typeof updateSEOMetaTags === 'function') {
        updateSEOMetaTags(
            `#${displayTagName} - Tagged Articles | Ferox Times`, 
            `Explore the latest news, updates, and deep-dive articles tagged with #${displayTagName} on Ferox Times.`, 
            '', 
            cleanTagUrl,
            `${displayTagName} news, latest ${displayTagName} updates, #${displayTagName}` 
        );
    }

    fetchTagResults(tagSlug, 1);
});