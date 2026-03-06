// js/saved.js
const articlesContainer = document.getElementById('articles-container');
const loader = document.getElementById('loader');
const errorDiv = document.getElementById('error-message');

function showLoader() { loader.style.display = 'block'; }
function hideLoader() { loader.style.display = 'none'; }
function showError(message) {
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => { errorDiv.style.display = 'none'; }, 5000);
}
function formatDate(isoString) {
    return new Date(isoString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function renderArticles(articles) {
    if (!articles || articles.length === 0) {
        articlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray);">You have no saved articles.</p>';
        return;
    }

    const html = articles.map(article => {
        const imageUrl = article.featured_image || 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
        const title = article.title || 'Untitled';
        const description = article.description || 'No description available.';
        const source = article.source_name || 'NewsHub';
        const date = article.published_at ? formatDate(article.published_at) : 'Unknown date';
        const articleId = article.id || '';

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
                        <button class="save-btn saved" data-id="${articleId}">Saved</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    articlesContainer.innerHTML = html;

    // Attach unsave functionality
    document.querySelectorAll('.save-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const articleId = btn.dataset.id;
            const success = await unsaveArticle(articleId); // Async call to backend
            
            if (success) {
                btn.closest('.article-card').remove();
                if (articlesContainer.children.length === 0) {
                    articlesContainer.innerHTML = '<p style="text-align: center; color: var(--gray);">You have no saved articles.</p>';
                }
            }
        });
    });
}

async function fetchSavedArticlesData() {
    showLoader();
    // Bookmark IDs local cache se li jayengi jo auth.js fetch karta hai
    const bookmarks = JSON.parse(localStorage.getItem('newsHub_bookmarks') || '[]');
    
    if (bookmarks.length === 0) {
        renderArticles([]);
        hideLoader();
        return;
    }

    try {
        // Backend se ek-ek karke saved articles ka data fetch karna
        const articlePromises = bookmarks.map(b => 
            fetch(`${CONFIG.API_BASE_URL}/news/articles/${b.article}/`)
                .then(res => res.ok ? res.json() : null)
        );
        
        const articles = await Promise.all(articlePromises);
        renderArticles(articles.filter(a => a !== null));
    } catch (e) {
        showError("Failed to load saved articles.");
    } finally {
        hideLoader();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser();
    if (!user) {
        window.location.href = 'login.html?redirect=saved.html';
        return;
    }
    fetchSavedArticlesData();
});