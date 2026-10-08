/* KitchenIQ — Notifications Page JS */
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

let allNotifs = [];
let filter = 'all';

const SEV_ICON = {
    info: 'fa-circle-info',
    success: 'fa-circle-check',
    warning: 'fa-triangle-exclamation',
    danger: 'fa-circle-exclamation',
};

const SEV_BG = {
    info: 'var(--kiq-brand-50)',
    success: 'var(--kiq-success-50)',
    warning: 'var(--kiq-warning-50)',
    danger: 'var(--kiq-danger-50)',
};

const SEV_COLOR = {
    info: 'var(--kiq-brand-600)',
    success: 'var(--kiq-success-600)',
    warning: 'var(--kiq-warning-600)',
    danger: 'var(--kiq-danger-600)',
};

function timeAgo(iso) {
    if (!iso) return '';
    const then = new Date(iso.replace(' ', 'T') + 'Z');
    const s = Math.floor((Date.now() - then) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

function render() {
    let list = allNotifs;
    if (filter === 'unread') list = list.filter(n => !n.is_read);
    else if (filter !== 'all') list = list.filter(n => n.severity === filter);

    const el = document.getElementById('notifList');

    if (!list.length) {
        el.innerHTML = `
            <div class="kiq-card" style="text-align: center; padding: 60px 20px;">
                <i class="fa-regular fa-bell-slash" style="font-size: 40px; color: var(--kiq-text-subtle); margin-bottom: 12px;"></i>
                <h3 style="font-size: 16px; margin-bottom: 4px;">No notifications</h3>
                <p style="color: var(--kiq-text-muted); font-size: 14px;">
                    ${filter === 'unread' ? 'You are all caught up!' : 'Notifications will appear here.'}
                </p>
            </div>`;
        return;
    }

    el.innerHTML = list.map(n => `
        <div class="kiq-card kiq-card-hover" data-id="${n.id}" data-link="${n.link || ''}"
             style="display: flex; gap: 14px; margin-bottom: 12px; cursor: pointer; ${!n.is_read ? 'border-left: 3px solid ' + SEV_COLOR[n.severity] + ';' : ''}">
            <div style="width: 40px; height: 40px; border-radius: 10px; background: ${SEV_BG[n.severity]}; color: ${SEV_COLOR[n.severity]}; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;">
                <i class="fa-solid ${SEV_ICON[n.severity] || 'fa-bell'}"></i>
            </div>
            <div style="flex: 1; min-width: 0;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 14px; color: var(--kiq-text);">${n.title}</div>
                        ${n.message ? `<div style="font-size: 13px; color: var(--kiq-text-muted); margin-top: 4px; line-height: 1.5;">${n.message}</div>` : ''}
                    </div>
                    <div style="font-size: 11px; color: var(--kiq-text-subtle); white-space: nowrap;">${timeAgo(n.created_at)}</div>
                </div>
                ${!n.is_read ? '<span class="kiq-badge kiq-badge-info" style="margin-top: 8px; font-size: 10px;">NEW</span>' : ''}
            </div>
        </div>
    `).join('');

    el.querySelectorAll('.kiq-card').forEach(card => {
        card.addEventListener('click', async () => {
            const id = card.dataset.id;
            const link = card.dataset.link;
            await fetch(API + `/api/notifications/${id}/read`, {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
            });
            if (link && link !== 'null') window.location.href = link;
            else load();
        });
    });
}

async function load() {
    try {
        const res = await fetch(`${API}/api/notifications/?limit=100`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        allNotifs = await res.json();
        render();
    } catch (e) {
        console.error(e);
    }
}

// Filter tabs
document.querySelectorAll('.kiq-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.kiq-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        filter = tab.dataset.filter;
        render();
    });
});

// Mark all read
document.getElementById('markAllBtn').addEventListener('click', async () => {
    await fetch(API + '/api/notifications/read-all', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token },
    });
    load();
});

// Test button
document.getElementById('testBtn').addEventListener('click', async () => {
    await fetch(API + '/api/notifications/test', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token },
    });
    load();
});

load();