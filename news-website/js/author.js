// js/author.js

// NAYA: Variable ka naam change kar diya gaya hai taaki clash na ho
const AUTHOR_API_URL = `${CONFIG.API_BASE_URL}/news`;

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
        // 1. Sabse pehle API se sirf Author ki details fetch karenge
        const authorResponse = await fetch(`${AUTHOR_API_URL}/authors/${authorId}/`);
        if (!authorResponse.ok) throw new Error('Author not found');
        
        const author = await authorResponse.json();

        // Extract author details
        // NAYA CODE: Global helper function for profile picture
        const avatar = window.getFullImageUrl(author.profile_picture, 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&q=80');
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

        // Dynamic SEO for Author
        if (typeof updateSEOMetaTags === 'function') {
            const seoBio = bio.length > 150 ? bio.substring(0, 150) + '...' : bio;
            updateSEOMetaTags(
                `${author.name} - NewsHub Author`, 
                seoBio, 
                avatar, 
                window.location.href,
                `${author.name}, journalist, author, NewsHub reporter` // <-- NAYA: Keywords
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
                    "name": "NewsHub"
                },
                "image": avatar,
                "description": bio,
                "url": window.location.href,
                "sameAs": []
            };

            if (author.twitter_url) personSchema.sameAs.push(author.twitter_url);
            if (author.linkedin_url) personSchema.sameAs.push(author.linkedin_url);

            injectSchema(personSchema);
        }
        // =======================================

        // 2. Ab is author ke likhe hue Articles fetch karenge
        const articlesResponse = await fetch(`${AUTHOR_API_URL}/articles/?author=${authorId}`);
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
            // NAYA CODE: Global helper function for article image
            const imageUrl = window.getFullImageUrl(article.featured_image, 'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?auto=format&fit=crop&w=300&q=80');
            
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