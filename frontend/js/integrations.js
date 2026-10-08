/* KitchenIQ — Integrations JS */
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

// Platform metadata
const PLATFORMS = [
    { key: 'zomato',  name: 'Zomato',  icon: 'Z', bg: '#e23744', text: '#fff' },
    { key: 'swiggy',  name: 'Swiggy',  icon: 'S', bg: '#fc8019', text: '#fff' },
    { key: 'pos',     name: 'POS',     icon: 'P', bg: '#4f46e5', text: '#fff' },
    { key: 'website', name: 'Website', icon: 'W', bg: '#0ea5e9', text: '#fff' },
];

let integrations = [];
let lastSyncLogs = [];

// ============================================================
// RENDER
// ============================================================
function renderGrid() {
    const grid = document.getElementById('integrationsGrid');

    grid.innerHTML = PLATFORMS.map(p => {
        const integ = integrations.find(i => i.platform === p.key);
        const isConnected = integ && integ.status === 'connected';
        const lastSync = integ && integ.last_sync_at
            ? new Date(integ.last_sync_at.replace(' ', 'T') + 'Z').toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
            : 'Never';

        return `
            <div class="kiq-card">
                <div style="display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 48px; height: 48px; border-radius: 12px; background: ${p.bg}; color: ${p.text}; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 22px;">
                            ${p.icon}
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 16px;">${p.name}</div>
                            <div style="font-size: 12px; color: var(--kiq-text-muted); margin-top: 2px;">
                                ${isConnected
                                    ? '<span style="color: var(--kiq-success-600);"><i class="fa-solid fa-circle" style="font-size: 8px;"></i> Connected</span>'
                                    : '<span style="color: var(--kiq-text-subtle);"><i class="fa-regular fa-circle" style="font-size: 8px;"></i> Not connected</span>'
                                }
                            </div>
                        </div>
                    </div>
                </div>

                ${isConnected ? `
                    <div style="font-size: 12px; color: var(--kiq-text-muted); margin-bottom: 16px;">
                        <i class="fa-regular fa-clock"></i> Last sync: ${lastSync}
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="kiq-btn kiq-btn-primary" onclick="syncPlatform('${p.key}', this)">
                            <i class="fa-solid fa-rotate"></i> Sync Now
                        </button>
                        <button class="kiq-btn kiq-btn-secondary" onclick="disconnectPlatform('${p.key}')">
                            Disconnect
                        </button>
                    </div>
                ` : `
                    <button class="kiq-btn kiq-btn-secondary kiq-btn-block" onclick="connectPlatform('${p.key}', this)">
                        <i class="fa-solid fa-plug"></i> Connect
                    </button>
                `}
            </div>`;
    }).join('');
}

function renderSyncHistory() {
    const el = document.getElementById('syncHistory');

    if (!lastSyncLogs.length) {
        el.innerHTML = '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No syncs yet. Connect a platform and click Sync Now.</p>';
        return;
    }

    el.innerHTML = `
        <table style="width: 100%; font-size: 14px;">
            <thead>
                <tr style="border-bottom: 1px solid var(--kiq-border);">
                    <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Platform</th>
                    <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Time</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Created</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Updated</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Status</th>
                </tr>
            </thead>
            <tbody>
                ${lastSyncLogs.map(log => `
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <td style="padding: 12px 0; font-weight: 500; text-transform: capitalize;">${log.platform}</td>
                        <td style="padding: 12px 0; color: var(--kiq-text-muted); font-size: 13px;">${log.time}</td>
                        <td style="padding: 12px 0; text-align: right;">${log.created}</td>
                        <td style="padding: 12px 0; text-align: right;">${log.updated}</td>
                        <td style="padding: 12px 0; text-align: right;">
                            <span class="kiq-badge kiq-badge-${log.status === 'success' ? 'success' : 'danger'}">${log.status}</span>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
}

// ============================================================
// API CALLS
// ============================================================
async function loadIntegrations() {
    const res = await fetch(`${API}/api/integrations/`, {
        headers: { 'Authorization': 'Bearer ' + token },
    });
    integrations = await res.json();
    renderGrid();
}

async function loadSyncLogs() {
    lastSyncLogs = [];

    for (const integ of integrations) {
        try {
            const res = await fetch(`${API}/api/integrations/${integ.id}/logs?limit=5`, {
                headers: { 'Authorization': 'Bearer ' + token },
            });
            const logs = await res.json();
            logs.forEach(l => {
                lastSyncLogs.push({
                    platform: integ.platform,
                    time: l.started_at ? new Date(l.started_at.replace(' ', 'T') + 'Z').toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—',
                    created: l.created,
                    updated: l.updated,
                    status: l.status,
                });
            });
        } catch (e) {}
    }

    lastSyncLogs.sort((a, b) => (b.time > a.time ? 1 : -1));
    renderSyncHistory();
}

// ============================================================
// ACTIONS
// ============================================================
window.connectPlatform = async function(platform, btn) {
    btn.disabled = true;
    const original = btn.innerHTML;
    btn.innerHTML = '<span class="kiq-spinner-dark kiq-spinner"></span> Connecting...';

    try {
        // Start OAuth flow
        const res = await fetch(`${API}/api/oauth/${platform}/start`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);

        // Redirect to OAuth consent page
        window.location.href = d.authorize_url;
    } catch (e) {
        if (window.showToast) window.showToast(e.message, 'danger');
        btn.disabled = false;
        btn.innerHTML = original;
    }
};

window.disconnectPlatform = async function(platform) {
    if (!confirm(`Disconnect ${platform}?`)) return;
    await fetch(`${API}/api/integrations/disconnect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ platform }),
    });
    await loadIntegrations();
    await loadSyncLogs();
};

window.syncPlatform = async function(platform, btn) {
    btn.disabled = true;
    const original = btn.innerHTML;
    btn.innerHTML = '<span class="kiq-spinner"></span> Syncing...';

    try {
        const res = await fetch(`${API}/api/integrations/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ platform, count: 15 }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);

        btn.innerHTML = `<i class="fa-solid fa-check"></i> +${d.created}`;
        btn.classList.remove('kiq-btn-primary');
        btn.classList.add('kiq-btn-success');

        setTimeout(async () => {
            await loadIntegrations();
            await loadSyncLogs();
        }, 800);

    } catch (err) {
        alert('Sync failed: ' + err.message);
        btn.disabled = false;
        btn.innerHTML = original;
    }
};

// ============================================================
// INIT
// ============================================================
async function init() {
    await loadIntegrations();
    await loadSyncLogs();
}

init();

// ============================================================
// OAuth Callback Notifications
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);

    if (params.get('oauth_success')) {
        const platform = params.get('oauth_success');
        if (window.showToast) window.showToast(`${platform.charAt(0).toUpperCase() + platform.slice(1)} connected successfully!`, 'success');
        // Clean URL
        window.history.replaceState({}, '', window.location.pathname);
        setTimeout(() => loadIntegrations(), 500);
    }

    if (params.get('oauth_error')) {
        const err = params.get('oauth_error');
        if (window.showToast) window.showToast(`Connection failed: ${err}`, 'danger');
        window.history.replaceState({}, '', window.location.pathname);
    }
});
