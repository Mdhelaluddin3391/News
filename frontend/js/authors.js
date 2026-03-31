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
            // Global helper function se profile picture URL nikalna
            const avatarUrl = window.getFullImageUrl(author.profile_picture, 'images/default-avatar.png');
            const avatarContainClass = avatarUrl.includes('default-avatar.png') ? 'img-contain' : '';
            const role = author.role || 'Contributor';
            
            // Social Media Links
            const twitterHtml = author.twitter_url ? `<a href="${author.twitter_url}" target="_blank" title="Twitter"><i class="fab fa-twitter"></i></a>` : '';
            const linkedinHtml = author.linkedin_url ? `<a href="${author.linkedin_url}" target="_blank" title="LinkedIn"><i class="fab fa-linkedin-in"></i></a>` : '';

            // Author Card HTML
            html += `
                <div class="author-card" onclick="window.location.href='/author?slug=${author.slug}'"'">
                    <img src="${avatarUrl}" alt="${author.name}" class="author-card-avatar ${avatarContainClass}" loading="lazy">
                    <h3 class="author-card-name">${author.name}</h3>
                    <div class="author-card-role">${role}</div>
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