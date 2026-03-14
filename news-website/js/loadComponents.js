async function loadComponents() {
    try {
        const headerPlaceholder = document.getElementById('header-placeholder');
        if (headerPlaceholder) {
            const headerRes = await fetch('components/header.html');
            headerPlaceholder.innerHTML = await headerRes.text();
            initHeaderScripts();
        }

        const footerPlaceholder = document.getElementById('footer-placeholder');
        if (footerPlaceholder) {
            const footerRes = await fetch('components/footer.html');
            footerPlaceholder.innerHTML = await footerRes.text();
        }

        if (typeof updateAuthUI === 'function') {
            updateAuthUI();
        }
    } catch (error) {
        console.error(error);
    }
}

function initHeaderScripts() {
    const menuBtn = document.getElementById("menuBtn");
    const mobileMenu = document.getElementById("mobileMenu");
    const closeBtn = document.getElementById("closeBtn");

    if (menuBtn && mobileMenu && closeBtn) {
        menuBtn.addEventListener("click", () => {
            mobileMenu.classList.add("active");
            document.body.classList.add("no-scroll");
        });
        
        closeBtn.addEventListener("click", () => {
            mobileMenu.classList.remove("active");
            document.body.classList.remove("no-scroll");
        });
    }

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
                window.location.href = `search.html?q=${encodeURIComponent(query)}`;
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

    if (nav && mainHeader) {
        // Calculate karte hain ki nav kab top par pahuchega
        const topBarHeight = topBar ? topBar.offsetHeight : 0;
        const scrollThreshold = topBarHeight + mainHeader.offsetHeight;

        window.addEventListener('scroll', () => {
            if (window.scrollY >= scrollThreshold) {
                nav.classList.add('sticky-nav');
                // Layout ko tootne se bachane ke liye mainHeader ke niche space dete hain
                mainHeader.style.marginBottom = nav.offsetHeight + 'px';
            } else {
                nav.classList.remove('sticky-nav');
                mainHeader.style.marginBottom = '0px';
            }
        });
    }
}

// 🔴 NAYA FUNCTION: Categories ko backend se laakar Header me set karne ke liye 🔴
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
        const currentCategory = urlParams.get('category') || 'general';

        let desktopHtml = `<li><a href="index.html?category=general" class="category-link ${currentCategory === 'general' ? 'active' : ''}">Home</a></li>`;
        let mobileHtml = `<a href="index.html?category=general" class="${currentCategory === 'general' ? 'active' : ''}">Home</a>`;
        let footerHtml = `<li><a href="index.html?category=general">General News</a></li>`;

        categories.forEach(cat => {
            const isActive = currentCategory === cat.slug ? 'active' : '';
            desktopHtml += `<li><a href="index.html?category=${cat.slug}" class="category-link ${isActive}">${cat.name}</a></li>`;
            mobileHtml += `<a href="index.html?category=${cat.slug}" class="${isActive}">${cat.name}</a>`;
            footerHtml += `<li><a href="index.html?category=${cat.slug}">${cat.name}</a></li>`;
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
            logoutUser();
            if (typeof updateAuthUI === 'function') updateAuthUI();
            window.location.href = 'index.html';
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
                
                topMatches.forEach(article => {
                    // Title mein query ko highlight karna (Case Insensitive)
                    const regex = new RegExp(`(${query})`, 'gi');
                    const highlightedTitle = article.title.replace(regex, '<span class="suggestion-highlight">$1</span>');
                    
                    html += `
                        <a href="article.html?id=${article.id}" class="suggestion-item">
                            <img src="${article.featured_image || 'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?w=50&q=80'}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">
                            <div style="flex: 1; min-width: 0;">
                                <div class="suggestion-title">${highlightedTitle}</div>
                                <div style="font-size: 0.75rem; color: var(--gray);">${article.category ? article.category.name : 'News'}</div>
                            </div>
                        </a>
                    `;
                });
                
                // Sabhi results dekhne ka button
                html += `
                    <a href="search.html?q=${encodeURIComponent(query)}" class="suggestion-item" style="justify-content: center; color: var(--primary); font-size: 0.9rem; font-weight: 600; background: #f8fafc; border-top: 1px solid var(--border);">
                        View all search results <i class="fas fa-arrow-right" style="font-size: 0.8rem; margin-left: 5px;"></i>
                    </a>
                `;

                suggestionsBox.innerHTML = html;
                suggestionsBox.style.display = 'block';
            } catch (e) {
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

document.addEventListener('DOMContentLoaded', loadComponents);


// ==================== GOOGLE ANALYTICS (GA4) INJECTOR ====================
async function injectGoogleAnalytics() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/settings/`);
        if (!response.ok) return;
        
        const data = await response.json();
        const trackingId = data.ga4_tracking_id;

        if (trackingId) {
            // 1. GTAG external script add karein
            const script1 = document.createElement('script');
            script1.async = true;
            script1.src = `https://www.googletagmanager.com/gtag/js?id=${trackingId}`;
            document.head.appendChild(script1);

            // 2. GTAG inline configuration add karein
            const script2 = document.createElement('script');
            script2.innerHTML = `
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${trackingId}');
            `;
            document.head.appendChild(script2);
            
            console.log(`✅ Google Analytics Initialized with ID: ${trackingId}`);
        }
    } catch (error) {
        console.error('Failed to load Google Analytics:', error);
    }
}

// Ye ensure karega ki DOM load hone ke baad GA4 load ho
document.addEventListener('DOMContentLoaded', () => {
    loadComponents();
    injectGoogleAnalytics(); // GA4 load karne ke liye function call
});