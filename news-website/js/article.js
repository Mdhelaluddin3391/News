// ==================== CONFIGURATION ====================
// Real API Endpoint pointing to your Django backend
const ARTICLE_DETAIL_API_URL = `${CONFIG.API_BASE_URL}/news/articles`;
let liveRefreshInterval;
let latestUpdateId = null; // NAYA: Track karne ke liye ki sabse latest update kaunsa hai
let liveSocket = null; // NAYA: WebSocket connection track karne ke liye
let useFallbackPolling = false; // NAYA: Fallback status track karne ke liye
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
    if (liveSocket) liveSocket.close(); // NAYA: Agar purana socket khula hai toh use band karein

    const user = getCurrentUser(); 
    const isSaved = user ? isArticleSaved(article.id) : false;
    
    const imageUrl = window.getFullImageUrl(article.featured_image, '');
    
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
        // NAYA: Pehli baar load hone par latest ID set kar lein
        if (article.live_updates && article.live_updates.length > 0) {
            latestUpdateId = article.live_updates[0].id;
        }

        liveUpdatesHTML = `
            <div class="live-updates-container" id="live-updates-section">
                <div class="live-updates-title">
                    <i class="fas fa-broadcast-tower" style="color: #e11d48;"></i> Live Updates
                </div>
                <div class="auto-refresh-indicator">
                    <i class="fas fa-sync-alt fa-spin"></i> Auto-refreshing for new updates...
                </div>
                <div class="timeline" id="timeline-container">
                    ${generateTimelineHTML(article.live_updates)}
                </div>
            </div>
        `;
        
        // NAYA: Yahan hum startLivePolling() ki jagah naya WebSocket function call kar rahe hain
        setTimeout(() => {
            initLiveUpdates(article.id);
        }, 100); 
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

// ==================== WEBSOCKET LOGIC WITH FALLBACK ====================
function initLiveUpdates(articleId) {
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    
    // API_BASE_URL (http://127.0.0.1:8000/api) se WebSocket URL banayein
    const backendBase = CONFIG.API_BASE_URL.replace('/api', '').replace('http', wsScheme);
    const wsUrl = `${backendBase}/ws/live-updates/${articleId}/`;

    try {
        liveSocket = new WebSocket(wsUrl);

        liveSocket.onopen = function(e) {
            console.log("✅ WebSocket connected for real-time live updates");
            const indicator = document.querySelector('.auto-refresh-indicator');
            if (indicator) {
                indicator.innerHTML = '<i class="fas fa-bolt" style="color: #f59e0b;"></i> Real-time updates active';
            }
        };

        liveSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.update_data) {
                appendNewUpdateToTimeline(data.update_data);
            }
        };

        liveSocket.onclose = function(e) {
            console.warn("⚠️ WebSocket closed. Falling back to polling...");
            fallbackToPolling(articleId);
        };

        liveSocket.onerror = function(e) {
            console.error("❌ WebSocket error. Falling back to polling...");
            // WebSocket ko close karenge taaki onclose event chal jaye aur fallback start ho
            if(liveSocket.readyState !== WebSocket.CLOSED) {
                liveSocket.close(); 
            }
        };
    } catch (err) {
        console.error("WebSocket setup failed:", err);
        fallbackToPolling(articleId);
    }
}

function fallbackToPolling(articleId) {
    if (useFallbackPolling) return; // Ek baar fallback shuru ho gaya toh dobara na karein
    useFallbackPolling = true;
    
    const indicator = document.querySelector('.auto-refresh-indicator');
    if (indicator) {
        indicator.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Connection weak. Auto-refreshing...';
    }
    
    // Aapka original polling function yahan call hoga
    startLivePolling(articleId); 
}

function appendNewUpdateToTimeline(update) {
    const timelineContainer = document.getElementById('timeline-container');
    if (!timelineContainer) return;

    // Remove empty message if exists
    const emptyMsg = timelineContainer.querySelector('p');
    if (emptyMsg && emptyMsg.textContent.includes('No live updates')) {
        emptyMsg.remove();
    }

    const timeStr = formatLiveTime(update.timestamp);
    const newHTML = `
        <div class="timeline-item" style="opacity: 0; transform: translateY(-20px);">
            <div class="timeline-dot"></div>
            <div class="timeline-time"><i class="far fa-clock"></i> ${timeStr}</div>
            <div class="timeline-content" style="background-color: #fecdd3; transition: background-color 2s ease;">
                ${update.title ? `<h4 class="timeline-title">${update.title}</h4>` : ''}
                <div class="timeline-body" style="line-height: 1.6; color: #334155;">${update.content}</div>
            </div>
        </div>
    `;

    // Sabse upar naya update daalein
    timelineContainer.insertAdjacentHTML('afterbegin', newHTML);

    // Smooth Animation
    const newItem = timelineContainer.firstElementChild;
    setTimeout(() => {
        newItem.style.opacity = '1';
        newItem.style.transform = 'translateY(0)';
        newItem.style.transition = 'all 0.5s ease';
        
        // Highlight color dheere-dheere hatayein
        setTimeout(() => {
            const content = newItem.querySelector('.timeline-content');
            if(content) content.style.backgroundColor = '#f8fafc';
        }, 2000);
    }, 50);

    latestUpdateId = update.id;
}

// ==================== AUTO-REFRESH POLLING (SMART UPDATE) ====================
function startLivePolling(articleId) {
    liveRefreshInterval = setInterval(async () => {
        try {
            // NAYA: '?_t=' + timestamp lagane se backend ka cache bypass ho jayega aur fresh data aayega
            const response = await fetch(`${ARTICLE_DETAIL_API_URL}/${articleId}/?_t=${new Date().getTime()}`);
            if (response.ok) {
                const article = await response.json();
                const timelineContainer = document.getElementById('timeline-container');
                
                if (timelineContainer && article.live_updates && article.live_updates.length > 0) {
                    // Check karein ki latest update ki ID kya hai
                    const currentLatestId = article.live_updates[0].id;
                    
                    // Agar naya update aaya hai, sirf tabhi HTML change karo
                    if (currentLatestId !== latestUpdateId) {
                        latestUpdateId = currentLatestId; // ID update kar lo
                        
                        // Pura HTML update karein
                        timelineContainer.innerHTML = generateTimelineHTML(article.live_updates);
                        
                        // Naye update par ek chota sa smooth highlight effect daalein taaki user ko pata chale
                        const firstItemContent = timelineContainer.querySelector('.timeline-content');
                        if (firstItemContent) {
                            firstItemContent.style.transition = 'background-color 1s ease';
                            firstItemContent.style.backgroundColor = '#fecdd3'; // Soft red highlight
                            
                            setTimeout(() => {
                                firstItemContent.style.backgroundColor = '#f8fafc'; // Wapas normal color
                            }, 2000);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Auto-refresh failed:', error);
        }
    }, 15000); // 30s se kam karke 15 seconds kar diya hai taaki live coverage tez ho
}

// Jab user kisi aur page par jaye, toh interval aur socket dono band kar dein
window.addEventListener('beforeunload', () => {
    // 1. Polling interval clear karein
    if (liveRefreshInterval) clearInterval(liveRefreshInterval);
    
    // 2. WebSocket connection securely close karein
    if (typeof liveSocket !== 'undefined' && liveSocket && liveSocket.readyState === WebSocket.OPEN) {
        liveSocket.close();
        console.log("WebSocket connection closed cleanly on page leave.");
    }
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