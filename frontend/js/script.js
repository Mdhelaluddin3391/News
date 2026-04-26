// js/script.js

const DEFAULT_SITE_NAME = 'Ferox Times';
const DEFAULT_SITE_DESCRIPTION = 'Stay updated with the latest breaking news, trending stories, and in-depth articles from around the world on Ferox Times.';
const PRODUCTION_CANONICAL_ORIGIN = 'https://www.feroxtimes.com';
const PRODUCTION_HOSTS = new Set(['feroxtimes.com', 'www.feroxtimes.com']);

function getCanonicalOrigin() {
    return PRODUCTION_HOSTS.has(window.location.hostname)
        ? PRODUCTION_CANONICAL_ORIGIN
        : window.location.origin;
}

const DEFAULT_SITE_IMAGE = getCanonicalOrigin() + '/images/default-news.png';

// ==================== GLOBAL HELPER FUNCTION (For Images) ====================
window.getFullImageUrl = function(imagePath, fallbackImage = '/images/default-news.png') {
    if (!imagePath) return fallbackImage;

    // Handle absolute URLs (from backend)
    if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
        // Since we're using Nginx gateway, convert backend URLs to relative paths
        try {
            const url = new URL(imagePath);
            if (url.pathname.startsWith('/media/')) {
                return url.pathname; // Use relative path for media files
            }
        } catch (e) {
            // Invalid URL, return as is
        }
        return imagePath;
    }

    // Handle relative paths
    if (imagePath.startsWith('/')) {
        return imagePath;
    }

    // Return as is for other cases
    return imagePath;
};

// ==================== TOAST NOTIFICATION SYSTEM ====================
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';

    toast.innerHTML = `<i class="fas ${icon} toast-icon" style="font-size: 1.2rem;"></i> <span></span>`;
    const toastMessage = toast.querySelector('span');
    if (toastMessage) {
        toastMessage.textContent = message;
    }
    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

// ==================== SEO META TAGS & CANONICAL UPDATER ====================
function normalizeMetaUrl(pageUrl) {
    const normalized = new URL(pageUrl || window.location.href, getCanonicalOrigin());
    normalized.hash = '';
    if (PRODUCTION_HOSTS.has(normalized.hostname)) {
        normalized.protocol = 'https:';
        normalized.hostname = 'www.feroxtimes.com';
        normalized.port = '';
    }
    if (normalized.pathname.length > 1) {
        normalized.pathname = normalized.pathname.replace(/\/+$/, '');
    }
    return normalized.toString();
}

function normalizeImageUrl(imageUrl) {
    const normalized = new URL(imageUrl || DEFAULT_SITE_IMAGE, getCanonicalOrigin());
    if (PRODUCTION_HOSTS.has(normalized.hostname)) {
        normalized.protocol = 'https:';
        normalized.hostname = 'www.feroxtimes.com';
        normalized.port = '';
    }
    return normalized.toString();
}

function setMetaTag(attrName, attrValue, content) {
    if (!content) return;
    let element = document.querySelector(`meta[${attrName}="${attrValue}"]`);
    if (!element) {
        element = document.createElement('meta');
        element.setAttribute(attrName, attrValue);
        document.head.appendChild(element);
    }
    element.setAttribute('content', content);
}

function ensureHeadMeta(name, content) {
    if (!content) return;
    let element = document.querySelector(`meta[name="${name}"]`);
    if (!element) {
        element = document.createElement('meta');
        element.setAttribute('name', name);
        document.head.appendChild(element);
    }
    element.setAttribute('content', content);
}

function ensureHeadLink(rel, href) {
    if (!href) return;
    let element = document.querySelector(`link[rel="${rel}"]`);
    if (!element) {
        element = document.createElement('link');
        element.setAttribute('rel', rel);
        document.head.appendChild(element);
    }
    element.setAttribute('href', href);
}

function updateSEOMetaTags(title, description, imageUrl, pageUrl, keywords = "", pageType = 'website', robots = 'index, follow') {
    const normalizedTitle = title || DEFAULT_SITE_NAME;
    document.title = normalizedTitle.includes(DEFAULT_SITE_NAME)
        ? normalizedTitle
        : `${normalizedTitle} | ${DEFAULT_SITE_NAME}`;

    const canonicalUrl = normalizeMetaUrl(pageUrl);
    const resolvedImageUrl = normalizeImageUrl(imageUrl);

    setMetaTag('name', 'description', description);
    if (keywords) {
        setMetaTag('name', 'keywords', keywords);
    }
    setMetaTag('name', 'robots', robots);

    // Update OG tags — prefer id-based elements (article page), fall back to selector
    const ogTitle = document.getElementById('og-title');
    if (ogTitle) ogTitle.setAttribute('content', normalizedTitle);
    else setMetaTag('property', 'og:title', normalizedTitle);

    const ogDesc = document.getElementById('og-description');
    if (ogDesc) ogDesc.setAttribute('content', description);
    else setMetaTag('property', 'og:description', description);

    const ogImage = document.getElementById('og-image');
    if (ogImage) ogImage.setAttribute('content', resolvedImageUrl);
    else setMetaTag('property', 'og:image', resolvedImageUrl);

    const ogUrl = document.getElementById('og-url');
    if (ogUrl) ogUrl.setAttribute('content', canonicalUrl);
    else setMetaTag('property', 'og:url', canonicalUrl);

    setMetaTag('property', 'og:type', pageType);
    setMetaTag('property', 'og:site_name', DEFAULT_SITE_NAME);

    // Update Twitter tags — prefer id-based elements, fall back to selector
    setMetaTag('name', 'twitter:card', 'summary_large_image');
    setMetaTag('name', 'twitter:site', '@feroxtimes');

    const twTitle = document.getElementById('twitter-title');
    if (twTitle) twTitle.setAttribute('content', normalizedTitle);
    else setMetaTag('name', 'twitter:title', normalizedTitle);

    const twDesc = document.getElementById('twitter-description');
    if (twDesc) twDesc.setAttribute('content', description);
    else setMetaTag('name', 'twitter:description', description);

    const twImage = document.getElementById('twitter-image');
    if (twImage) twImage.setAttribute('content', resolvedImageUrl);
    else setMetaTag('name', 'twitter:image', resolvedImageUrl);

    let canonicalTag = document.querySelector('link[rel="canonical"]');
    if (!canonicalTag) {
        canonicalTag = document.createElement('link');
        canonicalTag.setAttribute('rel', 'canonical');
        document.head.appendChild(canonicalTag);
    }
    canonicalTag.setAttribute('href', canonicalUrl);
}

// ==================== SCHEMA MARKUP (JSON-LD) INJECTOR ====================
function injectSchema(schemaData) {
    const existingSchema = document.getElementById('dynamic-schema');
    if (existingSchema) {
        existingSchema.remove();
    }

    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.id = 'dynamic-schema';
    
    if (Array.isArray(schemaData)) {
        const graphSchema = {
            "@context": "https://schema.org",
            "@graph": schemaData
        };
        script.text = JSON.stringify(graphSchema);
    } else {
        script.text = JSON.stringify(schemaData);
    }
    
    document.head.appendChild(script);
}

function getDefaultPageMetadata() {
    const pathname = window.location.pathname.replace(/\/+$/, '') || '/';
    const metadataByRoute = {
        '/': {
            title: 'Ferox Times - Breaking News, Global Reports & Analysis',
            description: 'Stay updated with the latest breaking news, trending stories, and in-depth analysis from around the world. Ferox Times delivers real-time reporting you can trust.',
            keywords: 'breaking news, world news, latest news, global updates, business news, technology news, Ferox Times',
            type: 'website',
            robots: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
        },
        '/404': {
            title: 'Page Not Found - Ferox Times',
            description: 'The page you requested could not be found on Ferox Times.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/about': {
            title: 'About Us - Ferox Times | Independent Global Journalism',
            description: 'Learn about Ferox Times — an independent digital journalism organization delivering accurate, real-time global news, investigative reporting, and expert analysis.',
            type: 'website',
            robots: 'index, follow'
        },
        '/advertise': {
            title: 'Advertise With Us - Ferox Times',
            description: 'Reach a global audience. Explore advertising opportunities, sponsorships, and brand partnerships with Ferox Times.',
            type: 'website',
            robots: 'index, follow'
        },
        '/authors': {
            title: 'Our Authors - Ferox Times Journalists & Contributors',
            description: 'Meet the award-winning journalists, editors, and expert contributors behind Ferox Times reporting.',
            type: 'website',
            robots: 'index, follow'
        },
        '/careers': {
            title: 'Careers at Ferox Times - Join Our Newsroom',
            description: 'Join the Ferox Times team. Browse open positions across editorial, product, and engineering at our global newsroom.',
            type: 'website',
            robots: 'index, follow'
        },
        '/contact': {
            title: 'Contact Us - Ferox Times',
            description: 'Get in touch with the Ferox Times editorial team for news tips, editorial inquiries, and partnership opportunities.',
            type: 'website',
            robots: 'index, follow'
        },
        '/cookie-policy': {
            title: 'Cookie Policy - Ferox Times',
            description: 'Read the Ferox Times cookie policy and learn how we use cookies and similar tracking technologies.',
            type: 'website',
            robots: 'index, follow'
        },
        '/editorial-guidelines': {
            title: 'Editorial Guidelines - Ferox Times',
            description: 'Our editorial standards, fact-checking processes, and journalistic values that guide every Ferox Times article.',
            type: 'website',
            robots: 'index, follow'
        },
        '/faq': {
            title: 'FAQ - Ferox Times Help Center',
            description: 'Answers to common questions about Ferox Times accounts, subscriptions, and editorial coverage.',
            type: 'website',
            robots: 'index, follow'
        },
        '/privacy': {
            title: 'Privacy Policy - Ferox Times',
            description: 'Review how Ferox Times collects, uses, and protects your personal data in compliance with global privacy regulations.',
            type: 'website',
            robots: 'index, follow'
        },
        '/terms': {
            title: 'Terms of Service - Ferox Times',
            description: 'Read the terms and conditions governing your use of Ferox Times and our digital services.',
            type: 'website',
            robots: 'index, follow'
        },
        // Private / session pages – deliberately noindex
        '/forgot-password': {
            title: 'Forgot Password - Ferox Times',
            description: 'Request a password reset for your Ferox Times account.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/login': {
            title: 'Login - Ferox Times',
            description: 'Access your Ferox Times account securely.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/profile': {
            title: 'My Profile - Ferox Times',
            description: 'Manage your Ferox Times account details and profile settings.',
            type: 'profile',
            robots: 'noindex, nofollow'
        },
        '/register': {
            title: 'Create an Account - Ferox Times',
            description: 'Register for a Ferox Times account to comment, save articles, and manage alerts.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/reset-password': {
            title: 'Reset Password - Ferox Times',
            description: 'Choose a new password for your Ferox Times account.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/saved': {
            title: 'Saved Articles - Ferox Times',
            description: 'Review the articles you saved for later reading on Ferox Times.',
            type: 'website',
            robots: 'noindex, nofollow'
        },
        '/unsubscribe': {
            title: 'Unsubscribe - Ferox Times',
            description: 'Manage your Ferox Times newsletter preferences.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/verify-email': {
            title: 'Verify Email - Ferox Times',
            description: 'Verify your email address to activate your Ferox Times account.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/write-article': {
            title: 'Write an Article - Ferox Times',
            description: 'Submit your article to the Ferox Times editorial team.',
            type: 'website',
            robots: 'noindex, nofollow'
        }
    };

    return metadataByRoute[pathname] || {
        title: document.title || DEFAULT_SITE_NAME,
        description: document.querySelector('meta[name="description"]')?.content || DEFAULT_SITE_DESCRIPTION,
        type: 'website'
    };
}

function ensureDefaultSeoMeta() {
    const metadata = getDefaultPageMetadata();
    ensureHeadMeta('theme-color', '#1a365d');
    ensureHeadMeta('color-scheme', 'light');
    ensureHeadLink('manifest', '/manifest.json');
    updateSEOMetaTags(
        metadata.title,
        metadata.description,
        DEFAULT_SITE_IMAGE,
        window.location.href,
        metadata.keywords || '',
        metadata.type || 'website',
        metadata.robots || 'index, follow'
    );
}

window.updateSEOMetaTags = updateSEOMetaTags;
window.injectSchema = injectSchema;

document.addEventListener('DOMContentLoaded', ensureDefaultSeoMeta);

// ==================== GLOBAL NEWSLETTER HANDLER ====================
document.addEventListener('submit', async (e) => {
    const form = e.target;
    // Check if the submitted form is a newsletter form
    if (form.id === 'newsletterForm' || form.classList.contains('newsletter-form')) {
        e.preventDefault();
        
        const emailInput = form.querySelector('input[type="email"]');
        if (!emailInput) return;
        const email = emailInput.value;
        const btn = form.querySelector('button[type="submit"]') || form.querySelector('button');

        if (btn) {
            btn.dataset.originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = 'Subscribing...';
        }

        try {
            // Prefer apiFetch from config/auth if available, fallback to fetch
            let response, data;
            
            if (typeof apiFetch === 'function' && typeof CONFIG !== 'undefined') {
                response = await apiFetch(`${CONFIG.API_BASE_URL}/newsletter/subscribe/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email })
                });
                data = await response.json().catch(() => ({}));
            } else {
                response = await fetch(`http://localhost:8000/api/newsletter/subscribe/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email })
                });
                data = await response.json().catch(() => ({}));
            }

            if (response.ok) {
                if(typeof showToast === 'function') showToast(data.message || 'Thank you for subscribing!', 'success');
                form.reset();
            } else {
                if(typeof showToast === 'function') showToast(data.error || 'Subscription failed.', 'error');
            }
        } catch (err) {
            console.error(err);
            if(typeof showToast === 'function') showToast('Network Error. Please try again later.', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = btn.dataset.originalText || 'Subscribe';
            }
        }
    }
});
