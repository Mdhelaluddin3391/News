// js/article.js
// ==================== CONFIGURATION ====================
// Real API Endpoint pointing to your Django backend
const ARTICLE_DETAIL_API_URL = `${CONFIG.API_BASE_URL}/news/articles`;
let liveRefreshInterval;

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

function formatLiveTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        hour: 'numeric',
        minute: 'numeric',
        hour12: true,
        month: 'short',
        day: 'numeric'
    });
}

// ==================== Render Article ====================
function renderArticle(article) {
    if (!article) {
        articleContainer.innerHTML = '<p style="text-align: center;">Article not found.</p>';
        return;
    }

    // Puraana refresh interval clear karein
    if (liveRefreshInterval) clearInterval(liveRefreshInterval);

    const user = getCurrentUser(); 
    const isSaved = user ? isArticleSaved(article.id) : false;
    
    const imageUrl = window.getFullImageUrl(article.featured_image, 'https://picsum.photos/1200/600?random=1');
    
    const title = article.title || 'Untitled';
    const source = article.source_name || 'NewsHub';
    const date = article.published_at ? formatArticleDate(article.published_at) : 'Unknown date';
    const description = article.description || '';
    const content = article.content || article.description || '';
    const categorySlug = article.category ? article.category.slug : 'general';
    const categoryName = article.category ? article.category.name : 'News';

    // --- TAGS HTML BLOCK AUR SEO KEYWORDS ---
    let tagsHTML = '';
    let seoKeywords = "news, daily news, breaking news"; // Default keywords
    
    if (article.tags && article.tags.length > 0) {
        tagsHTML = '<div class="article-tags">';
        // Tags array se comma-separated string banayein SEO ke liye
        seoKeywords = article.tags.map(t => t.name).join(', ');
        
        article.tags.forEach(tag => {
            tagsHTML += `<a href="tag.html?slug=${tag.slug}&name=${encodeURIComponent(tag.name)}" class="tag-pill">#${tag.name}</a>`;
        });
        tagsHTML += '</div>';
    }

    // Ek clean aur absolute canonical URL banayein
    const cleanPageUrl = `${window.location.origin}${window.location.pathname}?id=${article.id}`;

    // --- ADVANCED SEO META TAGS ---
    if (typeof updateSEOMetaTags === 'function') {
        const seoDescription = description.length > 150 ? description.substring(0, 150) + '...' : description;
        updateSEOMetaTags(title, seoDescription, imageUrl, cleanPageUrl, seoKeywords);
    }

    // --- ADVANCED ARTICLE & BREADCRUMB SCHEMA MARKUP ---
    if (typeof injectSchema === 'function') {
        const authorName = article.author ? article.author.name : 'NewsHub Staff';
        
        // 1. News Article Schema
        const articleSchema = {
            "@type": "NewsArticle",
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": cleanPageUrl
            },
            "headline": title,
            "image": [imageUrl],
            "datePublished": article.published_at || new Date().toISOString(),
            "dateModified": article.updated_at || article.published_at || new Date().toISOString(),
            "author": {
                "@type": "Person",
                "name": authorName,
                "url": article.author ? `${window.location.origin}/author.html?id=${article.author.id}` : window.location.origin
            },
            "publisher": {
                "@type": "Organization",
                "name": "NewsHub by Dharmanagar Live",
                "logo": {
                    "@type": "ImageObject",
                    "url": `${window.location.origin}/images/logo.png`
                }
            },
            "description": description.substring(0, 150)
        };

        // 2. Breadcrumb Schema (Google search results me nav structure dikhane ke liye)
        const breadcrumbSchema = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": `${window.location.origin}/index.html`
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": categoryName,
                    "item": `${window.location.origin}/index.html?category=${categorySlug}`
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": title,
                    "item": cleanPageUrl
                }
            ]
        };

        // Dono schemas ko array format me pass karein
        injectSchema([breadcrumbSchema, articleSchema]);
    }

    const saveButton = user ? 
        `<button class="save-btn detail-save-btn ${isSaved ? 'saved' : ''}" data-id="${article.id}">${isSaved ? 'Saved' : 'Save for Later'}</button>` 
        : '';

    // --- SOCIAL SHARING ---
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

    const relatedHTML = `<section class="related-articles"><h3>Related Articles</h3><div id="related-container"></div></section>`;
    const commentsHTML = `<section class="comments-section"><h3>Comments</h3><div id="comments-list"></div><div id="comment-form-container"></div></section>`;

    // ==================== LIVE UPDATES LOGIC ====================
    const liveBadgeHTML = article.is_live ? `<div class="live-badge"><i class="fas fa-circle"></i> LIVE UPDATE</div>` : '';
    
    let liveUpdatesHTML = '';
    if (article.is_live) {
        liveUpdatesHTML = `
            <div class="live-updates-container" id="live-updates-section">
                <div class="live-updates-title">
                    <i class="fas fa-broadcast-tower" style="color: #e11d48;"></i> Live Updates
                </div>
                <div class="auto-refresh-indicator">
                    <i class="fas fa-sync-alt fa-spin"></i> Auto-refreshing every 30 seconds...
                </div>
                <div class="timeline" id="timeline-container">
                    ${generateTimelineHTML(article.live_updates)}
                </div>
            </div>
        `;
        startLivePolling(article.id);
    }

    // --- MAIN HTML INJECTION ---
    const html = `
        <div class="detail-content" style="padding-bottom: 1rem;">
            ${liveBadgeHTML}
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
            
            ${liveUpdatesHTML}
            ${tagsHTML} 
            ${shareHTML}
            ${relatedHTML}
            ${commentsHTML}
            
            <div class="detail-actions">
                <a href="index.html" class="back-link">← Back to Home</a>
                ${saveButton}
            </div>
        </div>
    `;

    articleContainer.innerHTML = html;

    if (typeof renderRelated === 'function') renderRelated('related-container', categorySlug, article.id);
    if (typeof renderComments === 'function') renderComments(article.id, 'comments-list');

    // Save button event listener
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

// ==================== LIVE UPDATES TIMELINE HELPER ====================
function generateTimelineHTML(updates) {
    if (!updates || updates.length === 0) {
        return '<p style="color: var(--gray);">No live updates posted yet. Stay tuned!</p>';
    }

    let html = '';
    updates.forEach(update => {
        const timeStr = formatLiveTime(update.timestamp);
        html += `
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-time"><i class="far fa-clock"></i> ${timeStr}</div>
                <div class="timeline-content">
                    ${update.title ? `<h4 class="timeline-title">${update.title}</h4>` : ''}
                    <div class="timeline-body" style="line-height: 1.6; color: #334155;">${update.content}</div>
                </div>
            </div>
        `;
    });
    return html;
}

// ==================== AUTO-REFRESH POLLING ====================
function startLivePolling(articleId) {
    liveRefreshInterval = setInterval(async () => {
        try {
            const response = await fetch(`${ARTICLE_DETAIL_API_URL}/${articleId}/`);
            if (response.ok) {
                const article = await response.json();
                const timelineContainer = document.getElementById('timeline-container');
                
                // Agar timeline container exist karta hai aur naye updates aaye hain
                if (timelineContainer && article.live_updates) {
                    timelineContainer.innerHTML = generateTimelineHTML(article.live_updates);
                }
            }
        } catch (error) {
            console.error('Auto-refresh failed:', error);
        }
    }, 30000); // 30,000 ms = Har 30 seconds mein API hit karke update check karega
}

// Jab user kisi aur page par jaye, toh interval band kar dein
window.addEventListener('beforeunload', () => {
    if (liveRefreshInterval) clearInterval(liveRefreshInterval);
});


// ==================== Fetch Article ====================
async function fetchArticle(articleId) {
    showArticleLoader();
    clearArticleError();

    try {
        const response = await fetch(`${ARTICLE_DETAIL_API_URL}/${articleId}/`);
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        
        const article = await response.json();
        renderArticle(article);
    } catch (error) {
        console.error('Failed to fetch article:', error);
        showArticleError('Could not load the article. Please try again later.');
        articleContainer.innerHTML = ''; 
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
    
    // View count ko silently badhao
    incrementArticleView(articleId);
});

// ==================== Increment Views ====================
async function incrementArticleView(articleId) {
    const viewedKey = `viewed_article_${articleId}`;
    if (sessionStorage.getItem(viewedKey)) {
        return; // Agar pehle hi count ho gaya is session me, toh wapas laut jao
    }

    try {
        await fetch(`${ARTICLE_DETAIL_API_URL}/${articleId}/increment_view/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        sessionStorage.setItem(viewedKey, 'true');
    } catch (error) {
        console.error('Failed to increment views:', error);
    }
}