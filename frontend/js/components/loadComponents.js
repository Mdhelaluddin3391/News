async function loadComponents() {
    try {
        const headerPlaceholder = document.getElementById('header-placeholder');
        if (headerPlaceholder) {
            const headerRes = await fetch('/components/header');
            if (!headerRes.ok) {
                throw new Error(`Failed to load header (${headerRes.status})`);
            }
            headerPlaceholder.innerHTML = await headerRes.text();
            initHeaderScripts();
        }

        const footerPlaceholder = document.getElementById('footer-placeholder');
        if (footerPlaceholder) {
            const footerRes = await fetch('/components/footer');
            if (!footerRes.ok) {
                throw new Error(`Failed to load footer (${footerRes.status})`);
            }
            footerPlaceholder.innerHTML = await footerRes.text();
        }

        if (typeof updateAuthUI === 'function') {
            updateAuthUI();
        }

        document.dispatchEvent(new CustomEvent('layout:components-loaded'));
    } catch (error) {
        if (typeof window.reportFrontendError === 'function') {
            window.reportFrontendError(error, { scope: 'layout', action: 'loadComponents' });
        }
    }
}

function initHeaderScripts() {
    const menuBtn = document.getElementById("menuBtn");
    const mobileMenu = document.getElementById("mobileMenu");
    const closeBtn = document.getElementById("closeBtn");
    const mobileMenuBackdrop = document.getElementById("mobileMenuBackdrop");

    const toggleMobileMenu = (isOpen) => {
        if (!mobileMenu) return;
        mobileMenu.classList.toggle("active", isOpen);
        if (mobileMenuBackdrop) {
            mobileMenuBackdrop.classList.toggle("active", isOpen);
        }
        if (menuBtn) {
            menuBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
        }
        document.body.classList.toggle("no-scroll", isOpen);
        document.documentElement.classList.toggle("no-scroll", isOpen);
    };

    if (menuBtn && mobileMenu && closeBtn) {
        menuBtn.addEventListener("click", () => {
            toggleMobileMenu(true);
        });
        
        closeBtn.addEventListener("click", () => {
            toggleMobileMenu(false);
        });
    }

    if (mobileMenuBackdrop) {
        mobileMenuBackdrop.addEventListener("click", () => {
            toggleMobileMenu(false);
        });
    }

    if (mobileMenu) {
        mobileMenu.addEventListener("click", (event) => {
            if (event.target.closest("a[href]")) {
                toggleMobileMenu(false);
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && mobileMenu?.classList.contains("active")) {
            toggleMobileMenu(false);
        }
    });

    function updateDateTime() {
        const dateTimeEl = document.getElementById("dateTime");
        if (dateTimeEl) {
            dateTimeEl.innerText = new Date().toDateString() + " | " + new Date().toLocaleTimeString();
        }
    }
    updateDateTime();
    setInterval(updateDateTime, 1000);

    const inlineSearchForm = document.querySelector('.search-form-inline');
    if (inlineSearchForm) {
        inlineSearchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = inlineSearchForm.querySelector('input').value.trim();
            if (query) {
                // ✅ SEO FIX: Clean URL for search
                window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }
        });
    }

    // YAHAN HUMNE NAYA FUNCTION CALL KIYA HAI 👇
    fetchAndRenderNavCategories();
    setupSearchAutocomplete('desktop-search-input', 'desktop-suggestions');
    setupSearchAutocomplete('mobile-search-input', 'mobile-suggestions');

    // ==================== STICKY NAVBAR LOGIC ====================
    const nav = document.querySelector('nav');
    const topBar = document.querySelector('.top-bar');
    const mainHeader = document.querySelector('.main-header');
    const headerPlaceholder = document.getElementById('header-placeholder');

    const syncMobileHeaderOffset = () => {
        const stickyHeaderMedia = window.matchMedia('(max-width: 1024px)');
        const offset = stickyHeaderMedia.matches && headerPlaceholder ? headerPlaceholder.offsetHeight : 0;
        document.documentElement.style.setProperty('--mobile-header-offset', `${offset}px`);
    };

    window.syncMobileHeaderOffset = syncMobileHeaderOffset;

    if (nav && mainHeader) {
        const stickyHeaderMedia = window.matchMedia('(max-width: 1024px)');

        const syncStickyNav = () => {
            if (stickyHeaderMedia.matches) {
                nav.classList.remove('sticky-nav');
                mainHeader.style.marginBottom = '0px';
                return;
            }

            // Calculate karte hain ki nav kab top par pahuchega
            const topBarHeight = topBar ? topBar.offsetHeight : 0;
            const scrollThreshold = topBarHeight + mainHeader.offsetHeight;

            if (window.scrollY >= scrollThreshold) {
                nav.classList.add('sticky-nav');
                // Layout ko tootne se bachane ke liye mainHeader ke niche space dete hain
                mainHeader.style.marginBottom = nav.offsetHeight + 'px';
            } else {
                nav.classList.remove('sticky-nav');
                mainHeader.style.marginBottom = '0px';
            }
        };

        window.addEventListener('scroll', syncStickyNav);
        window.addEventListener('resize', () => {
            syncStickyNav();
            syncMobileHeaderOffset();
        });
        syncStickyNav();
    }

    syncMobileHeaderOffset();

    if (headerPlaceholder && typeof ResizeObserver !== 'undefined') {
        const headerResizeObserver = new ResizeObserver(() => {
            syncMobileHeaderOffset();
        });
        headerResizeObserver.observe(headerPlaceholder);
    }
}



async function fetchAndRenderNavCategories() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/news/categories/`);
        if (!response.ok) return;
        const data = await response.json();
        const categories = data.results || data;

        const desktopNav = document.getElementById('desktop-nav-categories');
        const mobileNav = document.getElementById('mobile-nav-categories');
        const footerNav = document.getElementById('footer-categories');

        // Check karte hain user kis category page par hai (taaki usko highlight kar sakein)
        const urlParams = new URLSearchParams(window.location.search);
        const pathParts = window.location.pathname.split('/').filter(Boolean);
        const currentCategory = urlParams.get('category')
            || (pathParts[0] === 'category' ? pathParts[1] : 'general');

        // ✅ SEO FIX: Clean URLs for navigation
        let desktopHtml = `<li><a href="/" class="category-link ${currentCategory === 'general' ? 'active' : ''}">Home</a></li>`;
        let mobileHtml = `<a href="/" class="${currentCategory === 'general' ? 'active' : ''}">Home</a>`;
        let footerHtml = `<li><a href="/">General News</a></li>`;

        categories.forEach(cat => {
            const isActive = currentCategory === cat.slug ? 'active' : '';
            const safeName = typeof window.escapeHtml === 'function' ? window.escapeHtml(cat.name || 'Category') : (cat.name || 'Category');
            // ✅ SEO FIX: Clean URLs for category links
            desktopHtml += `<li><a href="/category/${cat.slug}" class="category-link ${isActive}">${safeName}</a></li>`;
            mobileHtml += `<a href="/category/${cat.slug}" class="${isActive}">${safeName}</a>`;
            footerHtml += `<li><a href="/category/${cat.slug}">${safeName}</a></li>`;
        });

        if (desktopNav) desktopNav.innerHTML = desktopHtml;
        if (mobileNav) mobileNav.innerHTML = mobileHtml;
        if (footerNav) footerNav.innerHTML = footerHtml;

    } catch (error) {
        console.error('Failed to load categories for nav:', error);
    }
}


document.addEventListener('click', (e) => {
    const logoutBtn = e.target.closest('.logout-link') || e.target.closest('#logout-link') || e.target.closest('#logout-link-mobile');
    if (logoutBtn) {
        e.preventDefault();
        if (typeof logoutUser === 'function') {
            (async () => {
                await logoutUser();
                if (typeof updateAuthUI === 'function') updateAuthUI();
                // ✅ SEO FIX: Clean URL for home redirect
                window.location.href="/";
            })();
        }
    }
});

// ==================== AUTO COMPLETE SEARCH LOGIC ====================
function setupSearchAutocomplete(inputId, suggestionsId) {
    const input = document.getElementById(inputId);
    const suggestionsBox = document.getElementById(suggestionsId);
    if (!input || !suggestionsBox) return;

    let debounceTimer;

    input.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();

        if (query.length < 2) {
            suggestionsBox.style.display = 'none';
            return;
        }

        // 300ms ka debounce taaki har keypress par API hit na ho (Industry Standard)
        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(`${CONFIG.API_BASE_URL}/news/articles/?search=${encodeURIComponent(query)}`);
                if (!res.ok) return;
                const data = await res.json();
                const articles = data.results || data;

                if (articles.length === 0) {
                    suggestionsBox.innerHTML = '<div style="padding: 12px 15px; color: var(--gray); font-size: 0.9rem;">No matching articles found</div>';
                    suggestionsBox.style.display = 'block';
                    return;
                }

                // Top 5 results dikhayenge
                const topMatches = articles.slice(0, 5);
                let html = '';
                
                const highlightWords = (text, queryStr) => {
                    if (!text) return '';
                    let safeText = typeof window.escapeHtml === 'function' ? window.escapeHtml(text) : String(text);
                    const words = queryStr.split(/\\s+/).filter(w => w.length > 0);
                    words.forEach(word => {
                        const escapedWord = word.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
                        const regex = new RegExp(`(${escapedWord})`, 'gi');
                        safeText = safeText.replace(regex, '<span class="suggestion-highlight" style="background:#ffeeba; color:#000;">$1</span>');
                    });
                    return safeText;
                };

                topMatches.forEach(article => {
                    const highlightedTitle = highlightWords(article.title || 'Untitled', query);
                    const safeCategoryName = highlightWords(article.category ? article.category.name : 'News', query);
                    const imgUrl = article.featured_image || 'images/default-news.png';
                    const containClass = imgUrl.includes('default-news.png') ? 'img-contain' : '';
                    
                    let extraMatchesHtml = '';
                    
                    // Highlight Author Match
                    const authorName = article.author ? (article.author.name || article.author.user?.name || '') : 'Staff';
                    if (authorName && authorName.toLowerCase().includes(query.split(' ')[0].toLowerCase())) {
                        extraMatchesHtml += `<span style="margin-right:8px;"><i class="fas fa-user" style="font-size:0.7rem;"></i> By ${highlightWords(authorName, query)}</span>`;
                    }
                    
                    // Highlight Tags Match
                    if (article.tags && article.tags.length > 0) {
                        const matchedTags = article.tags.filter(t => query.split(' ').some(w => t.name.toLowerCase().includes(w.toLowerCase())));
                        if (matchedTags.length > 0) {
                           const tagsStr = matchedTags.map(t => `#${highlightWords(t.name, query)}`).join(' ');
                           extraMatchesHtml += `<span><i class="fas fa-hashtag" style="font-size:0.7rem;"></i> ${tagsStr}</span>`;
                        }
                    }

                    // ✅ SEO FIX: Clean URL for autocomplete article click
                    html += `
                        <a href="/article/${article.slug}" class="suggestion-item">
                            <img src="${imgUrl}" class="${containClass}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;" onerror="this.onerror=null; this.src='/images/default-news.png'; this.classList.add('img-contain');">
                            <div style="flex: 1; min-width: 0;">
                                <div class="suggestion-title">${highlightedTitle}</div>
                                <div style="font-size: 0.75rem; color: var(--gray); display:flex; align-items:center; flex-wrap:wrap;">
                                    <span style="font-weight:bold; margin-right:8px;">${safeCategoryName}</span>
                                    ${extraMatchesHtml}
                                </div>
                            </div>
                        </a>
                    `;
                });
                
                // Sabhi results dekhne ka button
                // ✅ SEO FIX: Clean URL for autocomplete view all
                html += `
                    <a href="/search?q=${encodeURIComponent(query)}" class="suggestion-item" style="justify-content: center; color: var(--primary); font-size: 0.9rem; font-weight: 600; background: #f8fafc; border-top: 1px solid var(--border);">
                        View all search results <i class="fas fa-arrow-right" style="font-size: 0.8rem; margin-left: 5px;"></i>
                    </a>
                `;

                suggestionsBox.innerHTML = html;
                suggestionsBox.style.display = 'block';
            } catch (e) {
                if (typeof window.reportFrontendError === 'function') {
                    window.reportFrontendError(e, { scope: 'layout', action: 'searchAutocomplete', query });
                }
                console.error('Autocomplete error:', e);
            }
        }, 300); 
    });

    // Agar kahin aur click kiya toh suggestion box band kar do
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !suggestionsBox.contains(e.target)) {
            suggestionsBox.style.display = 'none';
        }
    });

    // Input par dobara click karne se khul jaye
    input.addEventListener('focus', function() {
        if (this.value.trim().length >= 2 && suggestionsBox.innerHTML !== '') {
            suggestionsBox.style.display = 'block';
        }
    });
}

// ==================== GOOGLE ANALYTICS (GA4) INJECTOR ====================
async function injectGoogleAnalytics() {
    try {
        if (window.__gaInjected) {
            return;
        }

        const response = await fetch(`${CONFIG.API_BASE_URL}/settings/`);
        if (!response.ok) return;
        
        const data = await response.json();
        const trackingId = data.ga4_tracking_id;

        if (trackingId) {
            const existingScript = document.querySelector(`script[src*="googletagmanager.com/gtag/js?id=${trackingId}"]`);
            if (!existingScript) {
                const script1 = document.createElement('script');
                script1.async = true;
                script1.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(trackingId)}`;
                document.head.appendChild(script1);
            }

            window.dataLayer = window.dataLayer || [];
            window.gtag = window.gtag || function gtag() {
                window.dataLayer.push(arguments);
            };
            window.gtag('js', new Date());
            window.gtag('config', trackingId, {
                anonymize_ip: true,
                transport_type: 'beacon'
            });
            window.__gaInjected = true;
        }
    } catch (error) {
        if (typeof window.reportFrontendError === 'function') {
            window.reportFrontendError(error, { scope: 'analytics', action: 'injectGoogleAnalytics' });
        }
    }
}

// Ye ensure karega ki DOM load hone ke baad GA4 load ho
document.addEventListener('DOMContentLoaded', () => {
    loadComponents();
    injectGoogleAnalytics(); // GA4 load karne ke liye function call
});
