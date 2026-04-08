// js/author.js

// NAYA: Variable ka naam change kar diya gaya hai taaki clash na ho
const AUTHOR_API_URL = `${CONFIG.API_BASE_URL}/news`;

// Get Author ID from URL (e.g., /author/john-doe)
function getAuthorSlugFromUrl() {
    // ✅ SEO FIX: Support reading author from Clean URL path
    const pathParts = window.location.pathname.split('/').filter(Boolean);
    if (pathParts.length >= 2 && pathParts[0] === 'author') {
        return pathParts[1];
    }
    
    // Fallback to old query param approach
    const params = new URLSearchParams(window.location.search);
    return params.get('slug');
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}


async function fetchAuthorAndArticles() {
    const authorSlug = getAuthorSlugFromUrl();
    const authorCard = document.getElementById('author-details');
    const articlesContainer = document.getElementById('author-articles');

    if (!authorSlug) {
        authorCard.innerHTML = '<p>No author specified. Please select an author from an article.</p>';
        return;
    }

    // ✅ SEO FIX: Build clean URL for meta tags and schema
    const cleanAuthorUrl = `${window.location.origin}/author/${authorSlug}`;

    try {
        // 1. Sabse pehle API se sirf Author ki details fetch karenge
        const authorResponse = await fetch(`${AUTHOR_API_URL}/authors/${authorSlug}/`);
        if (!authorResponse.ok) throw new Error('Author not found');
        
        const author = await authorResponse.json();

        // Extract author details
        const avatar = window.getFullImageUrl(author.profile_picture, '/images/default-avatar.png');
        const avatarContainClass = avatar.includes('default-avatar.png') ? 'img-contain' : '';
        const role = author.role || 'Contributor';
        const bio = author.bio || 'This author has not added a bio yet.';
        const safeName = typeof window.escapeHtml === 'function' ? window.escapeHtml(author.name || 'Author') : (author.name || 'Author');
        const safeRole = typeof window.escapeHtml === 'function' ? window.escapeHtml(role) : role;
        const safeBio = typeof window.escapeHtml === 'function' ? window.escapeHtml(bio) : bio;
        const safeTwitterUrl = typeof window.getSafeHttpUrl === 'function' ? window.getSafeHttpUrl(author.twitter_url) : '';
        const safeLinkedinUrl = typeof window.getSafeHttpUrl === 'function' ? window.getSafeHttpUrl(author.linkedin_url) : '';
        
        const twitterHtml = safeTwitterUrl ? `<a href="${safeTwitterUrl}" target="_blank" rel="noopener noreferrer"><i class="fab fa-twitter"></i></a>` : '';
        const linkedinHtml = safeLinkedinUrl ? `<a href="${safeLinkedinUrl}" target="_blank" rel="noopener noreferrer"><i class="fab fa-linkedin"></i></a>` : '';

        // Render Author Profile
        authorCard.innerHTML = `
            <img src="${avatar}" alt="${safeName}" class="author-avatar ${avatarContainClass}">
            <div class="author-info">
                <h1>${safeName}</h1>
                <div class="author-role">${safeRole}</div>
                <p class="author-bio">${safeBio}</p>
                <div class="author-social">
                    ${twitterHtml}
                    ${linkedinHtml}
                </div>
            </div>
        `;

        // Dynamic SEO for Author
        if (typeof updateSEOMetaTags === 'function') {
            const seoBio = bio.length > 150 ? bio.substring(0, 150) + '...' : bio;
            updateSEOMetaTags(
                `${author.name} - Ferox Times Author`, 
                seoBio, 
                avatar, 
                cleanAuthorUrl, // ✅ SEO FIX: Use clean URL
                `${author.name}, journalist, author, Ferox Times reporter`,
                'profile'
            );
        }

        // === NAYA CODE: AUTHOR SCHEMA MARKUP ===
        if (typeof injectSchema === 'function') {
            const personSchema = {
                "@context": "https://schema.org",
                "@type": "Person",
                "name": author.name,
                "jobTitle": role,
                "worksFor": {
                    "@type": "Organization",
                    "name": "Ferox Times"
                },
                "image": avatar,
                "description": bio,
                "url": cleanAuthorUrl, // ✅ SEO FIX: Use clean URL
                "sameAs": []
            };

            if (author.twitter_url) personSchema.sameAs.push(author.twitter_url);
            if (author.linkedin_url) personSchema.sameAs.push(author.linkedin_url);

            injectSchema(personSchema);
        }
        // =======================================

        const articlesResponse = await fetch(`${AUTHOR_API_URL}/articles/?author__slug=${authorSlug}`);
        const articleData = await articlesResponse.json();
        const articles = articleData.results || articleData;

        // Agar author ne ek bhi article nahi likha hai
        if (articles.length === 0) {
            articlesContainer.innerHTML = '<p style="color: var(--gray);">This author has no published articles yet.</p>';
            return;
        }

        // Agar articles hain, toh unhe render karenge
        let articlesHtml = '';
        articles.forEach(article => {
            const date = article.published_at ? formatDate(article.published_at) : 'Unknown Date';
            const imageUrl = window.getFullImageUrl(article.featured_image, '/images/default-news.png');
            const containClass = imageUrl.includes('default-news.png') ? 'img-contain' : '';
            const safeTitle = typeof window.escapeHtml === 'function' ? window.escapeHtml(article.title || 'Untitled') : (article.title || 'Untitled');
            const safeDescription = typeof window.escapeHtml === 'function'
                ? window.escapeHtml(article.description || '')
                : (article.description || '');
            
            // ✅ SEO FIX: Use clean URL path for articles
            articlesHtml += `
                <div class="article-card">
                    <img src="${imageUrl}" alt="${safeTitle}" class="article-image ${containClass}">
                    <div class="article-content">
                        <h3 class="article-title">${safeTitle}</h3>
                        <p class="article-description">${safeDescription}</p>
                        <div class="article-meta">
                            <span class="article-date">${date}</span>
                            <a href="/article/${article.slug}" class="read-more">Read more →</a>
                        </div>
                    </div>
                </div>
            `;
        });
        
        articlesContainer.innerHTML = articlesHtml;

    } catch (error) {
        if (typeof window.reportFrontendError === 'function') {
            window.reportFrontendError(error, { scope: 'author', action: 'fetchAuthorAndArticles', authorSlug });
        }
        authorCard.innerHTML = '<p>Error loading author profile. Please try again later.</p>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchAuthorAndArticles();
});