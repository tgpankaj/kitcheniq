// ==========================================
// KitchenIQ — API Configuration
// Auto-detects environment
// ==========================================

(function () {
    var host = window.location.hostname;
    var isLocal = (host === "localhost" || host === "127.0.0.1" || host === "10.93.175.3");

    if (isLocal) {
        // Local development
        window.API_URL = "http://127.0.0.1:5050";
    } else {
        // Production — CHANGE THIS to your Render URL
        window.API_URL = "https://kitcheniq-api-xxxx.onrender.com";
    }
})();

// ============================================================
// Auto-attach X-Kitchen-Id header to all API calls
// ============================================================
(function() {
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        if (typeof url === "string" && window.API_URL && url.includes(window.API_URL)) {
            const kitchen = JSON.parse(localStorage.getItem("kitchen") || "{}");
            options.headers = options.headers || {};
            if (kitchen.id) {
                options.headers["X-Kitchen-Id"] = String(kitchen.id);
            }
        }
        return originalFetch.apply(this, arguments);
    };
})();
