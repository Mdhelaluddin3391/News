// js/ad-manager.js

const ADS_API_URL = `${CONFIG.API_BASE_URL}/ads/active/`;

async function loadAds() {
    // 1. Setup container references
    const adContainers = {
        header: document.getElementById('header-ad-container'),
        // Sidebar ads can be on index.html (sidebar-ad-1) or article.html (sidebar-sticky-ad)
        sidebar: [document.getElementById('sidebar-ad-1'), document.getElementById('sidebar-sticky-ad')],
        in_article: document.getElementById('article-top-ad')
    };

    try {
        const response = await fetch(ADS_API_URL);
        
        if (!response.ok) {
            console.log("No active ads or API error");
            return;
        }

        const adsData = await response.json();

        // 2. Handle Header Ad
        if (adContainers.header && adsData.header) {
            renderAd(adContainers.header, adsData.header);
        }

        // 3. Handle Sidebar Ads
        if (adsData.sidebar) {
            adContainers.sidebar.forEach(container => {
                if (container) renderAd(container, adsData.sidebar);
            });
        }

        // 4. Handle In-Article Ad
        if (adContainers.in_article && adsData.in_article) {
            renderAd(adContainers.in_article, adsData.in_article);
        }

    } catch (error) {
        console.error("Ads fetch error:", error);
    }
}

function renderAd(container, adData) {
    // Ad mil gayi hai, isliye container ko visible banayein
    container.style.display = 'flex'; 

    if (adData.ad_type === 'brand') {
        container.innerHTML = `
            <span class="ad-label" style="font-size: 10px; color: gray; display:block; text-align:center; margin-bottom: 5px; text-transform: uppercase;">Advertisement</span>
            <a href="${adData.url}" target="_blank" style="display:block; text-align:center;">
                <img src="${adData.image}" alt="Advertisement" style="max-width:100%; height:auto; border-radius: 5px; object-fit:contain;">
            </a>
        `;
        
        // Remove borders/background for clean header brand ads
        if(container.id === 'header-ad-container'){
            container.style.background = "transparent";
            container.style.border = "none";
        }
    } 
    else if (adData.ad_type === 'google') {
        container.innerHTML = `
            <span class="ad-label" style="font-size: 10px; color: gray; display:block; text-align:center; margin-bottom: 5px; text-transform: uppercase;">Advertisement</span>
            ${adData.google_ad_code}
        `;
        executeAdScripts(container);
    }
}

function executeAdScripts(container) {
    const scripts = container.getElementsByTagName('script');
    for (let i = 0; i < scripts.length; i++) {
        const newScript = document.createElement('script');
        if (scripts[i].src) {
            newScript.src = scripts[i].src;
            newScript.async = true;
            newScript.crossOrigin = "anonymous";
        } else {
            newScript.innerHTML = scripts[i].innerHTML;
        }
        document.body.appendChild(newScript);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Delay load for performance optimization (loads news first, then ads)
    setTimeout(loadAds, 1500);
});