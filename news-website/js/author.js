// js/author.js

const API_BASE_URL = `${CONFIG.API_BASE_URL}/news`;

// Get Author ID from URL (e.g., author.html?id=1)
function getAuthorIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('id');
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

async function fetchAuthorAndArticles() {
    const authorId = getAuthorIdFromUrl();
    const authorCard = document.getElementById('author-details');
    const articlesContainer = document.getElementById('author-articles');

    if (!authorId) {
        authorCard.innerHTML = '<p>No author specified. Please select an author from an article.</p>';
        return;
    }

    try {
        // Fetch articles by this author
        // Note: Make sure 'author' is added to filterset_fields in your backend's ArticleViewSet
        const response = await fetch(`${API_BASE_URL}/articles/?author=${authorId}`);
        if (!response.ok) throw new Error('Failed to fetch data');
        
        const data = await response.json();
        const articles = data.results || data;

        if (articles.length === 0) {
            authorCard.innerHTML = '<p>Author details not found or this author has no published articles.</p>';
            return;
        }

        // Extract author details from the first article
        const author = articles[0].author;
        const avatar = author.profile_picture || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&q=80';
        const role = author.role || 'Contributor';
        const bio = author.bio || 'This author has not added a bio yet.';
        
        const twitterHtml = author.twitter_url ? `<a href="${author.twitter_url}" target="_blank"><i class="fab fa-twitter"></i></a>` : '';
        const linkedinHtml = author.linkedin_url ? `<a href="${author.linkedin_url}" target="_blank"><i class="fab fa-linkedin"></i></a>` : '';

        // Render Author Profile
        authorCard.innerHTML = `
            <img src="${avatar}" alt="${author.name}" class="author-avatar">
            <div class="author-info">
                <h1>${author.name}</h1>
                <div class="author-role">${role}</div>
                <p class="author-bio">${bio}</p>
                <div class="author-social">
                    ${twitterHtml}
                    ${linkedinHtml}
                </div>
            </div>
        `;

        // Render Author's Articles
        let articlesHtml = '';
        articles.forEach(article => {
            const date = article.published_at ? formatDate(article.published_at) : 'Unknown Date';
            const imageUrl = article.featured_image || 'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?auto=format&fit=crop&w=300&q=80';
            
            articlesHtml += `
                <div class="article-card">
                    <img src="${imageUrl}" alt="${article.title}" class="article-image">
                    <div class="article-content">
                        <h3 class="article-title">${article.title}</h3>
                        <p class="article-description">${article.description}</p>
                        <div class="article-meta">
                            <span class="article-date">${date}</span>
                            <a href="article.html?id=${article.id}" class="read-more">Read more →</a>
                        </div>
                    </div>
                </div>
            `;
        });
        
        articlesContainer.innerHTML = articlesHtml;

    } catch (error) {
        console.error('Error fetching author data:', error);
        authorCard.innerHTML = '<p>Error loading author profile. Please try again later.</p>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchAuthorAndArticles();
});