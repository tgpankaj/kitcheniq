/* KitchenIQ — System Status JS */
const API = window.API_URL;
const token = localStorage.getItem('token');

try {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const name = user.full_name || user.email || 'User';
    document.getElementById('userName').textContent = name;
    document.getElementById('userAvatar').textContent =
        name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
} catch (e) {}

// ============================================================
// HEALTH
// ============================================================
async function loadHealth() {
    try {
        // Try monitoring ready first
        const res = await fetch(API + '/api/monitoring/ready', {
            headers: { 'Authorization': 'Bearer ' + token },
        });

        let data;
        if (res.ok) {
            data = await res.json();
        } else {
            // Fallback to /api/health
            const h = await fetch(API + '/api/health');
            data = { ready: h.ok, checks: { api: h.ok }, ready_fallback: true };
        }

        // Overall card
        const ready = data.ready || false;
        document.getElementById('overallStatus').textContent = ready ? '✅ Healthy' : '⚠️ Degraded';
        document.getElementById('overallDetail').textContent = ready
            ? 'All systems operational'
            : 'Some services need attention';

        const card = document.getElementById('overallCard');
        if (!ready) {
            card.style.background = 'linear-gradient(135deg, #7f1d1d 0%, #b91c1c 100%)';
        } else {
            card.style.background = 'linear-gradient(135deg, #1e3a8a 0%, #4f46e5 100%)';
        }

        // Checks list
        const checks = data.checks || {};
        const checkNames = {
            'database': { label: 'PostgreSQL', icon: 'fa-database' },
            'api': { label: 'Flask API', icon: 'fa-server' },
            'worker': { label: 'Background Worker', icon: 'fa-gear' },
        };

        document.getElementById('healthChecks').innerHTML = Object.entries(checks)
            .filter(([k]) => checkNames[k])
            .map(([key, value]) => {
                const meta = checkNames[key];
                const ok = value === true;
                return `
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid var(--kiq-border);">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 36px; height: 36px; border-radius: 8px; background: var(--kiq-bg-sunken); display: flex; align-items: center; justify-content: center; color: ${ok ? 'var(--kiq-success-600)' : 'var(--kiq-danger-600)'};">
                                <i class="fa-solid ${meta.icon}"></i>
                            </div>
                            <span style="font-weight: 500;">${meta.label}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px; font-size: 13px; color: ${ok ? 'var(--kiq-success-600)' : 'var(--kiq-danger-600)'};">
                            <span class="status-dot ${ok ? 'ok' : 'err'}"></span>
                            ${ok ? 'Operational' : 'Down'}
                        </div>
                    </div>
                `;
            }).join('') || '<p style="padding: 20px; color: var(--kiq-text-muted);">No checks available</p>';

    } catch (e) {
        document.getElementById('overallStatus').textContent = '❌ Offline';
        document.getElementById('overallDetail').textContent = 'Cannot reach backend';
        document.getElementById('healthChecks').innerHTML = '<p style="padding: 20px; color: var(--kiq-danger-600);">Backend unreachable</p>';
    }
}

// ============================================================
// APP INFO
// ============================================================
async function loadAppInfo() {
    try {
        const res = await fetch(API + '/api/monitoring/version', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        document.getElementById('appInfo').innerHTML = `
            <div style="display: grid; gap: 14px;">
                ${[
                    { label: 'Version', value: d.version, icon: 'fa-tag' },
                    { label: 'Environment', value: d.environment, icon: 'fa-cloud' },
                    { label: 'Uptime', value: d.uptime, icon: 'fa-clock' },
                    { label: 'Started At', value: d.started_at ? d.started_at.substring(0, 19).replace('T', ' ') : '—', icon: 'fa-play' },
                ].map(item => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0;">
                        <span style="color: var(--kiq-text-muted); font-size: 13px;">
                            <i class="fa-solid ${item.icon}" style="width: 16px;"></i> ${item.label}
                        </span>
                        <span style="font-weight: 500; font-size: 13px;">${item.value}</span>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (e) {
        document.getElementById('appInfo').innerHTML = '<p style="padding: 20px; color: var(--kiq-danger-600);">Failed to load</p>';
    }
}

// ============================================================
// METRICS
// ============================================================
async function loadMetrics() {
    try {
        const res = await fetch(API + '/api/monitoring/metrics', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        const db = d.database || {};
        const items = [
            { label: 'Users', value: db.users || 0, icon: 'fa-users', color: '#3b82f6' },
            { label: 'Kitchens', value: db.kitchens || 0, icon: 'fa-store', color: '#8b5cf6' },
            { label: 'Orders', value: db.orders || 0, icon: 'fa-receipt', color: '#10b981' },
            { label: 'Active Integrations', value: db.active_integrations || 0, icon: 'fa-plug', color: '#f59e0b' },
        ];

        document.getElementById('metricsGrid').innerHTML = items.map(it => `
            <div class="kiq-kpi">
                <div class="kiq-kpi-header">
                    <div class="kiq-kpi-label">${it.label}</div>
                    <div class="kiq-kpi-icon" style="background: ${it.color}20; color: ${it.color};">
                        <i class="fa-solid ${it.icon}"></i>
                    </div>
                </div>
                <div class="kiq-kpi-value">${Number(it.value).toLocaleString()}</div>
            </div>
        `).join('');

    } catch (e) {
        document.getElementById('metricsGrid').innerHTML = '<p style="grid-column: 1 / -1; text-align: center; color: var(--kiq-danger-600);">Failed to load</p>';
    }
}

// ============================================================
// ENDPOINT CHECKS
// ============================================================
async function loadEndpoints() {
    const checks = [
        { path: '/api/health', label: 'Health', auth: false },
        { path: '/api/dashboard/summary?days=7', label: 'Dashboard', auth: true },
        { path: '/api/analytics/dishes?days=7', label: 'Analytics', auth: true },
        { path: '/api/integrations/', label: 'Integrations', auth: true },
        { path: '/api/plans/current', label: 'Plans', auth: true },
        { path: '/api/team/me', label: 'Team', auth: true },
    ];

    const results = await Promise.all(checks.map(async (c) => {
        const start = Date.now();
        try {
            const headers = c.auth ? { 'Authorization': 'Bearer ' + token } : {};
            const res = await fetch(API + c.path, { headers });
            return {
                ...c,
                status: res.status,
                ok: res.ok,
                duration: Date.now() - start,
            };
        } catch (e) {
            return {
                ...c,
                status: 0,
                ok: false,
                duration: Date.now() - start,
                error: e.message,
            };
        }
    }));

    document.getElementById('endpoints').innerHTML = `
        <table style="width: 100%; font-size: 14px;">
            <thead>
                <tr style="border-bottom: 1px solid var(--kiq-border);">
                    <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Endpoint</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Status</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Response</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Time</th>
                </tr>
            </thead>
            <tbody>
                ${results.map(r => `
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <td style="padding: 12px 0;">
                            <code style="font-size: 12px; background: var(--kiq-bg-sunken); padding: 2px 6px; border-radius: 4px;">${r.path}</code>
                        </td>
                        <td style="padding: 12px 0; text-align: right;">
                            <span class="status-dot ${r.ok ? 'ok' : 'err'}"></span>
                            <span style="font-size: 13px; font-weight: 500;">${r.status || 'ERR'}</span>
                        </td>
                        <td style="padding: 12px 0; text-align: right; font-size: 13px; color: var(--kiq-text-muted);">
                            ${r.duration}ms
                        </td>
                        <td style="padding: 12px 0; text-align: right;">
                            <span class="kiq-badge kiq-badge-${r.ok ? 'success' : 'danger'}" style="font-size: 10px;">
                                ${r.ok ? 'OK' : 'FAIL'}
                            </span>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// ============================================================
// INIT
// ============================================================
function loadAll() {
    loadHealth();
    loadAppInfo();
    loadMetrics();
    loadEndpoints();
}

loadAll();
setInterval(loadAll, 15000);
