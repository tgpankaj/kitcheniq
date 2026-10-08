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

const CATEGORY_META = {
    auth:        { icon: 'fa-shield-halved',         color: '#3b82f6', label: 'Auth' },
    order:       { icon: 'fa-receipt',                color: '#10b981', label: 'Orders' },
    integration: { icon: 'fa-plug',                   color: '#8b5cf6', label: 'Integrations' },
    team:        { icon: 'fa-user-group',             color: '#f59e0b', label: 'Team' },
    settings:    { icon: 'fa-gear',                   color: '#64748b', label: 'Settings' },
    data:        { icon: 'fa-database',               color: '#0ea5e9', label: 'Data' },
    general:     { icon: 'fa-circle-info',            color: '#94a3b8', label: 'General' },
};

const ACTION_META = {
    login: '🔐 Logged in',
    login_failed: '❌ Login failed',
    signup: '🎉 Signed up',
    order_create: '📦 Order created',
    sync_success: '✅ Sync succeeded',
    sync_failed: '⚠️ Sync failed',
    member_added: '👤 Member added',
    member_removed: '👤 Member removed',
    kitchen_created: '🏪 Kitchen created',
    kitchen_updated: '✏️ Kitchen updated',
    csv_upload: '📤 CSV uploaded',
    export: '💾 Exported report',
};

function timeAgo(iso) {
    if (!iso) return '';
    const then = new Date(iso.replace(' ', 'T') + 'Z');
    const s = Math.floor((Date.now() - then) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    if (s < 604800) return Math.floor(s / 86400) + 'd ago';
    return then.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
}

// ============================================================
// LOAD SUMMARY CARDS
// ============================================================
async function loadSummary() {
    try {
        const res = await fetch(API + '/api/audit/summary', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        const totalEl = document.getElementById('catCards');
        totalEl.innerHTML = Object.entries(d.by_category || {}).map(([cat, count]) => {
            const meta = CATEGORY_META[cat] || CATEGORY_META.general;
            return `
                <div class="kiq-kpi" style="cursor: pointer;" onclick="filterByCategory('${cat}')">
                    <div class="kiq-kpi-header">
                        <div class="kiq-kpi-label">${meta.label}</div>
                        <div class="kiq-kpi-icon" style="background: ${meta.color}20; color: ${meta.color};">
                            <i class="fa-solid ${meta.icon}"></i>
                        </div>
                    </div>
                    <div class="kiq-kpi-value">${count}</div>
                    <span class="kiq-kpi-trend flat">last 30 days</span>
                </div>
            `;
        }).join('') || '<p style="grid-column: 1 / -1; text-align: center; color: var(--kiq-text-muted);">No activity yet.</p>';
    } catch (e) { console.error(e); }
}

// ============================================================
// LOAD ACTION LIST
// ============================================================
async function loadActions() {
    try {
        const res = await fetch(API + '/api/audit/actions', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const actions = await res.json();

        const sel = document.getElementById('actionFilter');
        sel.innerHTML = '<option value="">All actions</option>' +
            actions.map(a => `<option value="${a}">${ACTION_META[a] || a}</option>`).join('');
    } catch (e) { console.error(e); }
}

// ============================================================
// LOAD TIMELINE
// ============================================================
async function loadTimeline() {
    const days = document.getElementById('periodSelect').value;
    const category = document.getElementById('categoryFilter').value;
    const action = document.getElementById('actionFilter').value;

    let url = API + '/api/audit/?limit=100';
    if (days) url += '&days=' + days;
    if (category) url += '&category=' + category;
    if (action) url += '&action=' + action;

    try {
        const res = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const logs = await res.json();

        document.getElementById('timelineCount').textContent = `${logs.length} events`;

        const el = document.getElementById('timeline');

        if (!logs.length) {
            el.innerHTML = '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No activity in this period.</p>';
            return;
        }

        // Group by date
        const groups = {};
        logs.forEach(l => {
            const date = l.created_at ? l.created_at.split(' ')[0] : 'Unknown';
            if (!groups[date]) groups[date] = [];
            groups[date].push(l);
        });

        let html = '';
        Object.entries(groups).forEach(([date, items]) => {
            const dateLabel = new Date(date).toLocaleDateString('en-IN', {
                weekday: 'short', day: '2-digit', month: 'short', year: 'numeric'
            });

            html += `
                <div style="padding: 12px 0 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--kiq-text-subtle); border-top: 1px solid var(--kiq-border); margin-top: 12px;">
                    ${dateLabel}
                </div>
            `;

            items.forEach(l => {
                const meta = CATEGORY_META[l.category] || CATEGORY_META.general;
                const userName = l.user?.name || 'System';

                html += `
                    <div style="display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--kiq-border);">
                        <div style="width: 36px; height: 36px; border-radius: 10px; background: ${meta.color}20; color: ${meta.color}; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 15px;">
                            <i class="fa-solid ${meta.icon}"></i>
                        </div>
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-size: 14px; font-weight: 500; color: var(--kiq-text);">
                                ${l.description || (ACTION_META[l.action] || l.action)}
                            </div>
                            <div style="font-size: 12px; color: var(--kiq-text-muted); margin-top: 2px;">
                                <strong>${userName}</strong>
                                ${l.kitchen ? ' · ' + l.kitchen : ''}
                                ${l.ip ? ' · ' + l.ip : ''}
                            </div>
                        </div>
                        <div style="font-size: 11px; color: var(--kiq-text-subtle); white-space: nowrap; align-self: flex-start;">
                            ${timeAgo(l.created_at)}
                        </div>
                    </div>
                `;
            });
        });

        el.innerHTML = html;
    } catch (e) { console.error(e); }
}

// ============================================================
// FILTERS
// ============================================================
window.filterByCategory = function(cat) {
    document.getElementById('categoryFilter').value = cat;
    loadTimeline();
};

document.getElementById('periodSelect').addEventListener('change', loadTimeline);
document.getElementById('categoryFilter').addEventListener('change', loadTimeline);
document.getElementById('actionFilter').addEventListener('change', loadTimeline);

// ============================================================
// INIT
// ============================================================
loadSummary();
loadActions();
loadTimeline();
