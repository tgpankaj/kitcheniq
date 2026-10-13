// KitchenIQ — API Config (Production + Local)
(function () {
    var host = window.location.hostname;

    // Local dev
    if (host === 'localhost' || host === '127.0.0.1') {
        window.API_URL = 'http://127.0.0.1:5050';
        return;
    }

    // Production (Render)
    window.API_URL = 'https://kitcheniq-api-tos5.onrender.com';
})();