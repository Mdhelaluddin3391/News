// js/article.js
// ==================== CONFIGURATION ====================
// Real API Endpoint pointing to your Django backend
const ARTICLE_DETAIL_API_URL = `${CONFIG.API_BASE_URL}/news/articles`;

// ==================== DOM Elements ====================
const articleContainer = document.getElementById('article-detail');
// Variable names changed to avoid collision with script.js
const articleLoader = document.getElementById('loader');
const articleErrorDiv = document.getElementById('error-message');

// ==================== Helper Functions ====================
function showArticleLoader() {
    articleLoader.style.display = 'block';
    if (articleContainer) articleContainer.style.display = 'none';
}

function hideArticleLoader() {
    articleLoader.style.display = 'none';
    if (articleContainer) articleContainer.style.display = 'block';
}

function showArticleError(message) {
    articleErrorDiv.textContent = message;
    articleErrorDiv.style.display = 'block';
    setTimeout(() => {
        articleErrorDiv.style.display = 'none';
    }, 5000);
}

function clearArticleError() {
    articleErrorDiv.style.display = 'none';
}

function formatArticleDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric'
    });
}

// ==================== Render Article ====================
function renderArticle(article) {
    if (!article) {
        articleContainer.innerHTML = '<p style="text-align: center;">Article not found.</p>';
        return;
    }

    const user = getCurrentUser(); // Assuming this comes from auth.js
    const isSaved = user ? isArticleSaved(article.id) : false;
    
    // Mapping Django backend fields to frontend variables
    const imageUrl = article.featured_image || 'https://picsum.photos/1200/600?random=1';
    const title = article.title || 'Untitled';
    const source = article.source_name || 'NewsHub';
    const date = article.published_at ? formatArticleDate(article.published_at) : 'Unknown date';
    const description = article.description || '';
    const content = article.content || article.description || 'Full content is not available.';
    const categorySlug = article.category ? article.category.slug : 'general';

    if (typeof updateSEOMetaTags === 'function') {
        // Description lamba ho sakta hai, isliye hum use SEO ke liye thoda chota (truncate) kar lenge (approx 150 chars)
        const seoDescription = description.length > 150 ? description.substring(0, 150) + '...' : description;
        updateSEOMetaTags(title, seoDescription, imageUrl, window.location.href);
    }

    // --- NAYA TAGS HTML BLOCK ---
    let tagsHTML = '';
    if (article.tags && article.tags.length > 0) {
        tagsHTML = '<div class="article-tags">';
        article.tags.forEach(tag => {
            // Jab user tag par click kare, toh search.html par le jayenge
            tagsHTML += `<a href="tag.html?slug=${tag.slug}&name=${encodeURIComponent(tag.name)}" class="tag-pill">#${tag.name}</a>`;
        });
        tagsHTML += '</div>';
    }
    // ----------------------------

    const saveButton = user ? 
        `<button class="save-btn detail-save-btn ${isSaved ? 'saved' : ''}" data-id="${article.id}">${isSaved ? 'Saved' : 'Save for Later'}</button>` 
        : '';

    // Social sharing buttons (using current page URL)
    const backendShareUrl = `${CONFIG.API_BASE_URL}/news/articles/${article.id}/share/`;
    const shareUrl = encodeURIComponent(backendShareUrl);
    const shareTitle = encodeURIComponent(title);
    const shareHTML = `
        <div class="social-share">
            <h3>Share this article</h3>
            <div class="share-buttons">
                <a href="https://www.facebook.com/sharer/sharer.php?u=${shareUrl}" target="_blank" class="share-btn facebook">Facebook</a>
                <a href="https://twitter.com/intent/tweet?url=${shareUrl}&text=${shareTitle}" target="_blank" class="share-btn twitter">Twitter</a>
                <a href="https://wa.me/?text=${shareTitle}%20${shareUrl}" target="_blank" class="share-btn whatsapp">WhatsApp</a>
                <a href="https://www.linkedin.com/shareArticle?mini=true&url=${shareUrl}&title=${shareTitle}" target="_blank" class="share-btn linkedin">LinkedIn</a>
            </div>
        </div>
    `;

    // Related articles placeholder
    const relatedHTML = `
        <section class="related-articles">
            <h3>Related Articles</h3>
            <div id="related-container"></div>
        </section>
    `;

    // Comments placeholder
    const commentsHTML = `
        <section class="comments-section">
            <h3>Comments</h3>
            <div id="comments-list"></div>
            <div id="comment-form-container"></div>
        </section>
    `;

    // HTML ko inject karna, 'content' ab directly use hoga kyunki wo HTML format me aayega
    const html = `
        <div class="detail-content" style="padding-bottom: 1rem;">
            <h1 class="detail-title">${title}</h1>
            <div class="detail-meta" style="margin-bottom: 1rem; border-bottom: none;">
                <span class="detail-source">${source}</span>
                <span class="detail-date">${date}</span>
                <span><i class="far fa-eye"></i> ${article.views || 0} views</span>
            </div>
        </div>
        
        <img src="${imageUrl}" alt="${title}" class="detail-image">
        
        <div class="detail-content" style="padding-top: 2rem;">
            ${description ? `<p class="detail-description">${description}</p>` : ''}
            <div class="detail-body">
                ${content}
            </div>
            
            ${tagsHTML} ${shareHTML}
            ${relatedHTML}
            ${commentsHTML}
            <div class="detail-actions">
                <a href="index.html" class="back-link">← Back to Home</a>
                ${saveButton}
            </div>
        </div>
    `;

    articleContainer.innerHTML = html;

    // Load related articles (calls function from related.js)
    if (typeof renderRelated === 'function') {
        renderRelated('related-container', categorySlug, article.id);
    } else {
        console.warn('renderRelated function not available. Make sure related.js is loaded.');
    }

    // Load comments (calls function from comments.js)
    if (typeof renderComments === 'function') {
        renderComments(article.id, 'comments-list');
    } else {
        console.warn('renderComments function not available. Make sure comments.js is loaded.');
    }

    // Attach save button listener if user is logged in
    if (user) {
        const saveBtn = document.querySelector('.detail-save-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                const articleId = saveBtn.dataset.id;
                if (saveBtn.classList.contains('saved')) {
                    unsaveArticle(articleId);
                    saveBtn.classList.remove('saved');
                    saveBtn.textContent = 'Save for Later';
                } else {
                    saveArticle(article);
                    saveBtn.classList.add('saved');
                    saveBtn.textContent = 'Saved';
                }
            });
        }
    }
}

// ==================== Fetch Article ====================
async function fetchArticle(articleId) {
    showArticleLoader();
    clearArticleError();

    try {
        // Fetch specific article by ID from Django backend
        const response = await fetch(`${ARTICLE_DETAIL_API_URL}/${articleId}/`);
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        
        const article = await response.json();
        renderArticle(article);
    } catch (error) {
        console.error('Failed to fetch article:', error);
        showArticleError('Could not load the article. Please try again later.');
        articleContainer.innerHTML = ''; // clear any partial content
    } finally {
        hideArticleLoader();
    }
}

// ==================== Get ID from URL ====================
function getArticleIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('id');
}

// ==================== Initial Load ====================
document.addEventListener('DOMContentLoaded', () => {
    const articleId = getArticleIdFromUrl();
    if (!articleId) {
        showArticleError('No article ID specified.');
        articleContainer.innerHTML = '<p style="text-align: center;">Please select an article from the homepage.</p>';
        return;
    }
    
    // Pehle article fetch aur render karo
    fetchArticle(articleId);
    
    // NAYA CODE: View count ko silently badhao!
    incrementArticleView(articleId);
});

// ==================== Increment Views ====================
async function incrementArticleView(articleId) {
    // 1. Check karein ki kya is session mein pehle hi view count ho chuka hai?
    const viewedKey = `viewed_article_${articleId}`;
    if (sessionStorage.getItem(viewedKey)) {
        console.log("View already counted for this session.");
        return; // Agar pehle hi count ho gaya, toh yahin se wapas laut jao
    }

    try {
        await fetch(`${ARTICLE_DETAIL_API_URL}/${articleId}/increment_view/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // 2. API call success hone ke baad, browser ki memory mein likh do ki view count ho gaya
        sessionStorage.setItem(viewedKey, 'true');
        
    } catch (error) {
        console.error('Failed to increment views:', error);
    }
}