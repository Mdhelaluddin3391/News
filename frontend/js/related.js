// js/related.js
// ==================== RELATED ARTICLES MODULE ====================

const RELATED_API_URL = `${CONFIG.API_BASE_URL}/news/articles/`;

// Helper function to calculate time ago
function getRelatedTimeAgo(isoString) {
    if (!isoString) return 'Just now';
    const now = new Date();
    const past = new Date(isoString);
    const diffMs = now - past;
    const diffHrs = Math.floor(diffMs / 3600000);
    if (diffHrs < 1) return 'Just now';
    if (diffHrs < 24) return `${diffHrs} hour${diffHrs > 1 ? 's' : ''} ago`;
    const diffDays = Math.floor(diffHrs / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

// Fetch related articles based on current article's category
async function fetchRelatedArticles(categorySlug, currentArticleId) {
    try {
        // Backend se same category ke articles fetch karna
        const response = await fetch(`${RELATED_API_URL}?category__slug=${categorySlug}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch related articles');
        }
        
        const data = await response.json();
        const articles = data.results || data; // Handle paginated response
        
        // Current article ko filter out karna taaki wo khud related list mein na dikhe
        const related = articles.filter(a => a.id != currentArticleId);
        
        // Sirf top 3 articles return karna
        return related.slice(0, 3);
        
    } catch (error) {
        console.error('Error fetching related articles:', error);
        return [];
    }
}

// Render related articles in container
async function renderRelated(containerId, categorySlug, currentArticleId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Optional: Show loading state
    container.innerHTML = '<p style="color: var(--gray); font-size: 0.9rem;">Loading related articles...</p>';

    const related = await fetchRelatedArticles(categorySlug, currentArticleId);
    
    if (related.length === 0) {
        container.innerHTML = '<p>No related articles found.</p>';
        return;
    }

    let html = '';
    related.forEach(a => {
        // NAYA CODE: Global helper function for image URL (Production ready)
        const imageUrl = window.getFullImageUrl(a.featured_image, 'images/default-news.png');
        const timeAgo = getRelatedTimeAgo(a.published_at);
        const liveBadge = a.is_live ? `<div class="related-live-badge"><i class="fas fa-circle" style="font-size: 6px;"></i> LIVE</div>` : '';
        
        html += `
            <div class="related-card">
                <a href="article.html?id=${a.id}">
                    ${liveBadge}
                    <img src="${imageUrl}" alt="${a.title}" loading="lazy">
                    <div class="related-content">
                        <h4>${a.title}</h4>
                        <div class="related-meta-time"><i class="far fa-clock"></i> ${timeAgo}</div>
                    </div>
                </a>
            </div>
        `;
    });
    
    container.innerHTML = html;
}