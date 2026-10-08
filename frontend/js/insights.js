/* KitchenIQ — AI Insights JS */
const API = window.API_URL;
const token = localStorage.getItem('token');

if (!token) window.location.href = 'login.html';

try {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const name = user.full_name || user.email || 'User';
    document.getElementById('userName').textContent = name;
    document.getElementById('userAvatar').textContent =
        name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
} catch (e) {}

document.getElementById('logoutBtn').addEventListener('click', (e) => {
    e.preventDefault();
    localStorage.clear();
    window.location.href = 'login.html';
});

const TYPE_META = {
    danger:  { label: 'Review',       icon: 'fa-triangle-exclamation', badge: 'badge-danger' },
    warning: { label: 'Optimize',     icon: 'fa-wrench',               badge: 'badge-warning' },
    info:    { label: 'Opportunity',  icon: 'fa-lightbulb',            badge: 'badge-info' },
    success: { label: 'Promote',      icon: 'fa-arrow-up-right-dots',  badge: 'badge-success' },
};

let allInsights = [];
let activeFilter = 'all';

// ============================================================
// RENDER
// ============================================================
function renderInsights() {
    const grid = document.getElementById('insightsGrid');

    let list = allInsights;
    if (activeFilter !== 'all') {
        list = allInsights.filter(i => i.type === activeFilter);
    }

    // Search
    const q = document.getElementById('searchInput').value.toLowerCase().trim();
    if (q) {
        list = list.filter(i =>
            i.title.toLowerCase().includes(q) ||
            i.reason.toLowerCase().includes(q) ||
            i.category.toLowerCase().includes(q)
        );
    }

    if (!list.length) {
        grid.innerHTML = `
            <div class="kiq-card" style="text-align: center; padding: 60px 20px;">
                <i class="fa-solid fa-inbox" style="font-size: 40px; color: var(--kiq-text-subtle); margin-bottom: 12px;"></i>
                <h3 style="font-size: 16px; margin-bottom: 4px;">No insights found</h3>
                <p style="color: var(--kiq-text-muted); font-size: 14px;">Upload more data or sync a platform to see insights.</p>
            </div>`;
        return;
    }

    grid.innerHTML = list.map(i => {
        const meta = TYPE_META[i.type] || TYPE_META.info;
        const metricsHtml = Object.entries(i.metrics || {}).map(([k, v]) => `
            <div style="font-size: 12px; color: var(--kiq-text-muted);">
                <span style="font-weight: 500;">${k}:</span> ${v}
            </div>
        `).join('');

        return `
            <div class="insight-card insight-${i.type}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; gap: 12px;">
                    <div style="flex: 1;">
                        <span class="insight-badge ${meta.badge}">
                            <i class="fa-solid ${meta.icon}"></i> ${meta.label}
                        </span>
                        <div style="font-size: 11px; color: var(--kiq-text-subtle); margin-left: 8px;">${i.category}</div>
                        <h3 style="font-size: 16px; font-weight: 600; margin-top: 4px;">${i.title}</h3>
                        <p style="font-size: 13px; color: var(--kiq-text-muted); margin-top: 6px; line-height: 1.5;">${i.reason}</p>
                    </div>
                </div>

                ${metricsHtml ? `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; padding: 12px; background: var(--kiq-bg-sunken); border-radius: 8px; margin: 12px 0;">
                        ${metricsHtml}
                    </div>
                ` : ''}

                <div style="background: linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%); border-left: 3px solid #3b82f6; padding: 10px 14px; border-radius: 6px; font-size: 13px; color: #1e40af;">
                    <strong style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 2px;">Recommended Action</strong>
                    ${i.action}
                </div>
            </div>
        `;
    }).join('');
}

// ============================================================
// LOAD
// ============================================================
async function loadInsights() {
    const days = document.getElementById('periodSelect').value;

    try {
        const [insightsRes, summaryRes] = await Promise.all([
            fetch(`${API}/api/insights/?days=${days}`, { headers: { 'Authorization': 'Bearer ' + token } }),
            fetch(`${API}/api/insights/summary?days=${days}`, { headers: { 'Authorization': 'Bearer ' + token } }),
        ]);

        allInsights = await insightsRes.json();
        const summary = await summaryRes.json();

        document.getElementById('kpiDanger').textContent = summary.by_type.danger || 0;
        document.getElementById('kpiWarning').textContent = summary.by_type.warning || 0;
        document.getElementById('kpiInfo').textContent = summary.by_type.info || 0;
        document.getElementById('kpiSuccess').textContent = summary.by_type.success || 0;

        renderInsights();
    } catch (err) {
        console.error('Insights load failed:', err);
    }
}

// ============================================================
// FILTERS
// ============================================================
document.querySelectorAll('.kiq-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.kiq-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        activeFilter = tab.dataset.filter;
        renderInsights();
    });
});

document.getElementById('searchInput').addEventListener('input', renderInsights);
document.getElementById('periodSelect').addEventListener('change', loadInsights);

loadInsights();