/* KitchenIQ — Landing Page JS */
const API = window.API_URL;

// ============================================================
// NAVBAR SCROLL EFFECT
// ============================================================
window.addEventListener('scroll', () => {
    const nav = document.getElementById('navbar');
    if (window.scrollY > 20) {
        nav.classList.add('scrolled');
    } else {
        nav.classList.remove('scrolled');
    }
});

// ============================================================
// SMOOTH SCROLL FOR ANCHOR LINKS
// ============================================================
document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
        const target = document.querySelector(a.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// ============================================================
// LOAD PLANS FOR PRICING PREVIEW
// ============================================================
async function loadPlans() {
    try {
        const res = await fetch(API + '/api/public/plans');
        const plans = await res.json();

        const grid = document.getElementById('pricingGrid');

        grid.innerHTML = plans.map(p => {
            const isFree = p.price === 0;
            const price = p.price;
            const popular = p.popular;

            return `
                <div class="landing-price-card ${popular ? 'popular' : ''}">
                    ${popular ? '<span class="landing-price-badge">Most Popular</span>' : ''}
                    <div class="landing-price-name">${p.name}</div>
                    <div class="landing-price-value">₹${price.toLocaleString('en-IN')}</div>
                    <div class="landing-price-period">${isFree ? 'free forever' : 'per month'}</div>

                    <ul class="landing-price-features">
                        ${p.features.slice(0, 5).map(f => `<li><i class="fa-solid fa-check"></i><span>${f}</span></li>`).join('')}
                    </ul>

                    <a href="signup.html" class="landing-btn-primary" style="justify-content: center; width: 100%; height: 44px;">
                        ${isFree ? 'Start Free' : 'Start Trial'} <i class="fa-solid fa-arrow-right"></i>
                    </a>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Failed to load plans:', e);
        document.getElementById('pricingGrid').innerHTML = '<p style="text-align:center; padding: 40px; grid-column: 1 / -1; color: var(--kiq-text-muted);">Unable to load pricing right now.</p>';
    }
}

// ============================================================
// LOAD STATS (Optional - could add testimonials)
// ============================================================
async function loadStats() {
    try {
        const res = await fetch(API + '/api/public/stats');
        const stats = await res.json();
        console.log('[landing] Stats:', stats);
        // Could display these if we add a stats section
    } catch (e) {
        console.log('[landing] Stats unavailable');
    }
}

// ============================================================
// SCROLL ANIMATION FOR FEATURES
// ============================================================
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px',
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

document.querySelectorAll('.landing-feature').forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = `all 0.5s ease ${i * 0.05}s`;
    observer.observe(el);
});

// ============================================================
// INIT
// ============================================================
loadPlans();
loadStats();
