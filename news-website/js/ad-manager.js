// js/ad-manager.js

// Aapke backend ka Ad API endpoint
const ADS_API_URL = `${CONFIG.API_BASE_URL}/ads/active/`;

async function loadAds() {
    try {
        // Backend se ads ka data fetch karna
        const response = await fetch(ADS_API_URL);
        
        if (!response.ok) {
            console.log("No active ads or API error");
            return;
        }

        const adsData = await response.json();
        // Backend se data is format me aayega:
        // { header: { ad_type: 'brand', image: 'url', ... }, sidebar: { ad_type: 'google', google_ad_code: '...' } }

        // 1. Header Ad Handle Karna
        const headerAdContainer = document.getElementById('header-ad-container');
        if (headerAdContainer && adsData.header) {
            renderAd(headerAdContainer, adsData.header);
        }

        // 2. Sidebar Ad Handle Karna
        // Dhyan dein: Aapne sidebar me id "sidebar-ad-1" di hai
        const sidebarAdContainer = document.getElementById('sidebar-ad-1');
        if (sidebarAdContainer && adsData.sidebar) {
            renderAd(sidebarAdContainer, adsData.sidebar);
        }

    } catch (error) {
        console.error("Ads fetch karne mein error:", error);
    }
}

// Universal function jo check karega ki Ad "brand" ki hai ya "google" ki
function renderAd(container, adData) {
    if (adData.ad_type === 'brand') {
        // Brand Ad dikhana (Image + Link)
        container.innerHTML = `
            <span class="ad-label" style="font-size: 10px; color: gray; display:block; text-align:center; margin-bottom: 5px; text-transform: uppercase;">Advertisement</span>
            <a href="${adData.url}" target="_blank" style="display:block; text-align:center;">
                <img src="${adData.image}" alt="Advertisement" style="max-width:100%; height:auto; border-radius: 5px; object-fit:contain;">
            </a>
        `;
        
        // Agar header banner hai toh background transparent kar do
        if(container.id === 'header-ad-container'){
            container.style.background = "transparent";
            container.style.border = "none";
        }
    } 
    else if (adData.ad_type === 'google') {
        // Google Ad dikhana (Script)
        container.innerHTML = `
            <span class="ad-label" style="font-size: 10px; color: gray; display:block; text-align:center; margin-bottom: 5px; text-transform: uppercase;">Advertisement</span>
            ${adData.google_ad_code}
        `;
        
        // IMPORTANT: Browser directly innerHTML se dali gayi <script> ko execute nahi karta.
        // Google adsense ki script run karne ke liye hume custom function call karna hoga:
        executeAdScripts(container);
    }
}

// Helper function: Google Adsense ki scripts ko browser mein force execute karne ke liye
function executeAdScripts(container) {
    const scripts = container.getElementsByTagName('script');
    for (let i = 0; i < scripts.length; i++) {
        const newScript = document.createElement('script');
        // Agar script me src hai (jaise adsbygoogle.js)
        if (scripts[i].src) {
            newScript.src = scripts[i].src;
            newScript.async = true;
            newScript.crossOrigin = "anonymous";
        } 
        // Agar inline script hai (jaise (adsbygoogle = window.adsbygoogle || []).push({});)
        else {
            newScript.innerHTML = scripts[i].innerHTML;
        }
        document.body.appendChild(newScript);
    }
}

// Jab page (aur components) load ho jaye, tab ads load karein
document.addEventListener('DOMContentLoaded', () => {
    // Thoda delay (1.5 seconds) de rahe hain taaki pehle news articles fast load ho jayein
    setTimeout(loadAds, 1500);
});