// js/saved.js
const savedArticlesContainer = document.getElementById('articles-container');
const savedLoader = document.getElementById('loader');
const savedErrorDiv = document.getElementById('error-message');

function showSavedLoader() { savedLoader.style.display = 'block'; }
function hideSavedLoader() { savedLoader.style.display = 'none'; }
function showSavedError(message) {
    savedErrorDiv.textContent = message;
    savedErrorDiv.style.display = 'block';
    setTimeout(() => { savedErrorDiv.style.display = 'none'; }, 5000);
}
function formatSavedDate(isoString) {
    return new Date(isoString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function renderSavedArticles(articles) {
    if (!articles || articles.length === 0) {
        savedArticlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray);">You have no saved articles.</p>';
        return;
    }

    const html = articles.map(article => {
        // NAYA CODE: Global helper function for image URL (Production ready)
        const imageUrl = window.getFullImageUrl(article.featured_image, 'images/default-news.png');
        const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
        
        const title = article.title || 'Untitled';
        const description = article.description ? (article.description.length > 110 ? article.description.substring(0, 110) + '...' : article.description) : 'No description available.';
        const source = article.source_name || 'Ferox Times';
        const date = article.published_at ? formatSavedDate(article.published_at) : 'Unknown date';
        const articleId = article.id || '';

        return `
            <div class="article-card">
                <img src="${imageUrl}" alt="${title}" class="article-image ${containClass}" loading="lazy">
                <div class="article-content">
                    <h3 class="article-title">${title}</h3>
                    <p class="article-description">${description}</p>
                    <div class="article-meta">
                        <span class="article-source">${source}</span>
                        <span class="article-date">${date}</span>
                        <a href="/article.html?slug=${article.slug}" class="read-more">Read more →</a>
                        <button class="save-btn saved" data-id="${articleId}">Saved</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    savedArticlesContainer.innerHTML = html;

    // Attach unsave functionality
    document.querySelectorAll('.save-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const articleId = btn.dataset.id;
            const success = await unsaveArticle(articleId); // Async call to backend
            
            if (success) {
                btn.closest('.article-card').remove();
                if (savedArticlesContainer.children.length === 0) {
                    savedArticlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray);">You have no saved articles.</p>';
                }
            }
        });
    });
}

async function fetchSavedArticlesData() {
    showSavedLoader();
    // Bookmark IDs local cache se li jayengi jo auth.js fetch karta hai
    const bookmarks = JSON.parse(localStorage.getItem('feroxTimes_bookmarks') || '[]');
    
    if (bookmarks.length === 0) {
        renderSavedArticles([]);
        hideSavedLoader();
        return;
    }

    try {
        // Backend se ek-ek karke saved articles ka data fetch karna
        const articlePromises = bookmarks.map(b => 
            fetch(`${CONFIG.API_BASE_URL}/news/articles/${b.article}/`)
                .then(res => res.ok ? res.json() : null)
        );
        
        const articles = await Promise.all(articlePromises);
        renderSavedArticles(articles.filter(a => a !== null));
    } catch (e) {
        showSavedError("Failed to load saved articles.");
    } finally {
        hideSavedLoader();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser();
    if (!user) {
        window.location.href="/login.html?redirect=/saved.html";
        return;
    }
    fetchSavedArticlesData();
});