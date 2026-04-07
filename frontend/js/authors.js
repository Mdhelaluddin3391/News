// js/authors.js
const AUTHORS_API_URL = `${CONFIG.API_BASE_URL}/news/authors/`;

async function fetchAndRenderAuthors() {
    const container = document.getElementById('authors-container');
    const loader = document.getElementById('loader');
    const errorDiv = document.getElementById('error-message');

    if (!container) return;

    // Show loader
    if (loader) loader.style.display = 'block';
    if (errorDiv) errorDiv.style.display = 'none';
    container.innerHTML = '';

    try {
        const response = await fetch(AUTHORS_API_URL);
        if (!response.ok) {
            throw new Error('Failed to fetch authors data');
        }

        const data = await response.json();
        // DRF usually returns paginated data in 'results'
        const authors = data.results || data;

        if (authors.length === 0) {
            container.innerHTML = '<p style="text-align:center; grid-column: 1/-1; color: var(--gray);">No authors found.</p>';
            return;
        }

        let html = '';
        authors.forEach(author => {
            // Global helper function se profile picture URL nikalna - NAYA UPDATE: added slash /
            const avatarUrl = window.getFullImageUrl(author.profile_picture, '/images/default-avatar.png');
            const avatarContainClass = avatarUrl.includes('default-avatar.png') ? 'img-contain' : '';
            const role = author.role || 'Contributor';
            const safeName = typeof window.escapeHtml === 'function' ? window.escapeHtml(author.name || 'Author') : (author.name || 'Author');
            const safeRole = typeof window.escapeHtml === 'function' ? window.escapeHtml(role) : role;
            const safeTwitterUrl = typeof window.getSafeHttpUrl === 'function' ? window.getSafeHttpUrl(author.twitter_url) : '';
            const safeLinkedinUrl = typeof window.getSafeHttpUrl === 'function' ? window.getSafeHttpUrl(author.linkedin_url) : '';
            
            // Social Media Links
            const twitterHtml = safeTwitterUrl ? `<a href="${safeTwitterUrl}" target="_blank" rel="noopener noreferrer" title="Twitter"><i class="fab fa-twitter"></i></a>` : '';
            const linkedinHtml = safeLinkedinUrl ? `<a href="${safeLinkedinUrl}" target="_blank" rel="noopener noreferrer" title="LinkedIn"><i class="fab fa-linkedin-in"></i></a>` : '';

            // ✅ SEO FIX: Added clean URL routing and an actual <a> tag so search engine bots can crawl to the author profile
            html += `
                <div class="author-card" onclick="window.location.href='/author/${author.slug}'" style="cursor: pointer;">
                    <img src="${avatarUrl}" alt="${safeName}" class="author-card-avatar ${avatarContainClass}" loading="lazy">
                    <h3 class="author-card-name">
                        <a href="/author/${author.slug}" style="text-decoration: none; color: inherit;">${safeName}</a>
                    </h3>
                    <div class="author-card-role">${safeRole}</div>
                    <div class="author-card-social" onclick="event.stopPropagation();">
                        ${twitterHtml}
                        ${linkedinHtml}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;

    } catch (error) {
        console.error('Error fetching authors:', error);
        if (errorDiv) {
            errorDiv.textContent = 'Could not load authors. Please try again later.';
            errorDiv.style.display = 'block';
        }
    } finally {
        if (loader) loader.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchAndRenderAuthors();
});