// js/related.js
// ==================== RELATED ARTICLES MODULE ====================

const RELATED_API_URL = `${CONFIG.API_BASE_URL}/news/articles/`;

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
        const imageUrl = window.getFullImageUrl(a.featured_image, 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80');
        
        html += `
            <div class="related-card">
                <a href="article.html?id=${a.id}">
                    <img src="${imageUrl}" alt="${a.title}" loading="lazy">
                    <div class="related-content">
                        <h4>${a.title}</h4>
                    </div>
                </a>
            </div>
        `;
    });
    
    container.innerHTML = html;
}