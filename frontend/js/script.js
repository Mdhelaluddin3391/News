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

    setMetaTag('property', 'og:title', normalizedTitle);
    setMetaTag('property', 'og:description', description);
    setMetaTag('property', 'og:image', resolvedImageUrl);
    setMetaTag('property', 'og:url', canonicalUrl);
    setMetaTag('property', 'og:type', pageType);
    setMetaTag('property', 'og:site_name', DEFAULT_SITE_NAME);

    setMetaTag('name', 'twitter:card', 'summary_large_image');
    setMetaTag('name', 'twitter:title', normalizedTitle);
    setMetaTag('name', 'twitter:description', description);
    setMetaTag('name', 'twitter:image', resolvedImageUrl);

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
            title: 'Ferox Times - Premium Global News',
            description: DEFAULT_SITE_DESCRIPTION,
            keywords: 'global news, breaking news, latest updates, world news, Ferox Times',
            type: 'website'
        },
        '/404': {
            title: 'Page Not Found',
            description: 'The page you requested could not be found on Ferox Times.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/about': {
            title: 'About Ferox Times',
            description: 'Learn more about Ferox Times, our mission, vision, and editorial standards.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/advertise': {
            title: 'Advertise With Us',
            description: 'Explore advertising opportunities, sponsorships, and brand partnerships with Ferox Times.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/authors': {
            title: 'Our Authors',
            description: 'Meet the journalists, editors, and contributors behind Ferox Times.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/careers': {
            title: 'Careers',
            description: 'Join the Ferox Times team across editorial, product, and engineering roles.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/contact': {
            title: 'Contact Us',
            description: 'Get in touch with the Ferox Times editorial and support teams.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/cookie-policy': {
            title: 'Cookie Policy',
            description: 'Read the Ferox Times cookie policy and learn how cookies are used on the site.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/faq': {
            title: 'Frequently Asked Questions',
            description: 'Answers to common questions about Ferox Times subscriptions, accounts, and editorial coverage.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/forgot-password': {
            title: 'Forgot Password',
            description: 'Request a password reset for your Ferox Times account.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/login': {
            title: 'Login',
            description: 'Access your Ferox Times account securely.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/privacy': {
            title: 'Privacy Policy',
            description: 'Review how Ferox Times collects, uses, and protects your personal data.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/profile': {
            title: 'My Profile',
            description: 'Manage your Ferox Times account details and profile settings.',
            type: 'profile',
            robots: 'noindex, nofollow'
        },
        '/register': {
            title: 'Create an Account',
            description: 'Register for a Ferox Times account to comment, save articles, and manage alerts.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/reset-password': {
            title: 'Set New Password',
            description: 'Choose a new password for your Ferox Times account.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/saved': {
            title: 'Saved Articles',
            description: 'Review the articles you saved to read later on Ferox Times.',
            type: 'website',
            robots: 'noindex, nofollow'
        },
        '/terms': {
            title: 'Terms of Service',
            description: 'Read the terms and conditions governing use of Ferox Times.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/unsubscribe': {
            title: 'Unsubscribe',
            description: 'Manage or confirm your Ferox Times newsletter unsubscribe request.',
            type: 'website',
            robots: 'noindex, follow'
        },
        '/verify-email': {
            title: 'Verify Email',
            description: 'Verify your email address to activate your Ferox Times account.',
            type: 'website',
            robots: 'noindex, follow'
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
