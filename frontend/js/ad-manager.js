// Function ko global (window) bana diya hai taaki article.js isko call kar sake
window.fetchActiveAds = function() {
    const adsApiUrl = window.CONFIG?.API_BASE_URL
        ? `${window.CONFIG.API_BASE_URL}/ads/active/`
        : "/api/ads/active/";

    // API call ads lane ke liye
    fetch(adsApiUrl)
        .then(response => response.json())
        .then(data => {
            const slots = ['header', 'sidebar', 'in_article'];
            
            slots.forEach(slot => {
                const adData = data[slot];
                const adContainer = document.getElementById(`ad-${slot}`);
                
                if (adData && adContainer) {
                    let adContent = '';
                    
                    if (adData.ad_type === 'brand') {
                        // Image Ad banayein
                        const imageUrl = adData.image; 
                        const linkUrl = adData.url || '#';
                        adContent = `<a href="${linkUrl}" target="_blank" rel="noopener noreferrer">
                                        <img src="${imageUrl}" alt="Ad" style="max-width: 100%; height: auto; border-radius: 8px;">
                                     </a>`;
                    } else if (adData.ad_type === 'google') {
                        // Google Ad code dalein
                        adContent = adData.google_ad_code;
                    }
                    
                    adContainer.innerHTML = adContent;
                    adContainer.style.display = 'block'; // Ad aane par hi div show hoga
                    
                    // Google AdSense script run karein
                    if (adData.ad_type === 'google') {
                        try {
                            (adsbygoogle = window.adsbygoogle || []).push({});
                        } catch (e) {
                            console.error("AdSense error:", e);
                        }
                    }
                }
            });
        })
        .catch(error => console.error("Error fetching ads:", error));
};

// Auto-load Logic
document.addEventListener("DOMContentLoaded", function() {
    // Agar URL mein 'article.html' NAHI hai, tabhi page load par ad show karein
    // (Article page par article load hone ke baad ad aayegi)
    if (!window.location.pathname.includes('article.html')) {
        window.fetchActiveAds();
    }
});