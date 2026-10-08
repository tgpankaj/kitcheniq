/* KitchenIQ — Settings JS */
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

// Toast helper
function toast(msg, type = 'success') {
    const colors = { success: '#10b981', danger: '#ef4444', info: '#3b82f6' };
    const el = document.createElement('div');
    el.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 9999;
        background: ${colors[type]}; color: white;
        padding: 12px 20px; border-radius: 8px;
        font-size: 14px; font-weight: 500;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        transition: all 0.3s ease;
        transform: translateX(100%); opacity: 0;
    `;
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(() => {
        el.style.transform = 'translateX(0)';
        el.style.opacity = '1';
    });
    setTimeout(() => {
        el.style.transform = 'translateX(100%)';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 300);
    }, 3000);
}

// ============================================================
// LOAD
// ============================================================
async function loadProfile() {
    try {
        const res = await fetch(`${API}/api/settings/profile`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        document.getElementById('profEmail').value = d.user.email;
        document.getElementById('profName').value = d.user.full_name || '';

        if (d.kitchen) {
            document.getElementById('kitName').value = d.kitchen.name || '';
            document.getElementById('kitCity').value = d.kitchen.city || '';
            document.getElementById('kitAddress').value = d.kitchen.address || '';
            document.getElementById('kitPhone').value = d.kitchen.phone || '';
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadStats() {
    try {
        const res = await fetch(`${API}/api/settings/stats`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        document.getElementById('statOrders').textContent = d.total_orders;
        document.getElementById('statDishes').textContent = d.total_dishes;
        document.getElementById('statCustomers').textContent = d.total_customers;
    } catch (e) {
        console.error(e);
    }
}

// ============================================================
// SAVE PROFILE
// ============================================================
document.getElementById('profileForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="kiq-spinner"></span> Saving...';

    try {
        const res = await fetch(`${API}/api/settings/profile`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ full_name: document.getElementById('profName').value }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);

        // Update localStorage
        const u = JSON.parse(localStorage.getItem('user') || '{}');
        u.full_name = document.getElementById('profName').value;
        localStorage.setItem('user', JSON.stringify(u));

        // Update header
        document.getElementById('userName').textContent = u.full_name;

        toast('Profile updated successfully');
    } catch (err) {
        toast(err.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
    }
});

// ============================================================
// SAVE KITCHEN
// ============================================================
document.getElementById('kitchenForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="kiq-spinner"></span> Saving...';

    try {
        const res = await fetch(`${API}/api/settings/kitchen`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({
                name: document.getElementById('kitName').value,
                city: document.getElementById('kitCity').value,
                address: document.getElementById('kitAddress').value,
                phone: document.getElementById('kitPhone').value,
            }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);

        // Update localStorage
        const k = JSON.parse(localStorage.getItem('kitchen') || '{}');
        k.name = document.getElementById('kitName').value;
        localStorage.setItem('kitchen', JSON.stringify(k));

        toast('Kitchen details updated');
    } catch (err) {
        toast(err.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
    }
});

// ============================================================
// CHANGE PASSWORD
// ============================================================
document.getElementById('passwordForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const curr = document.getElementById('currPass').value;
    const nw = document.getElementById('newPass').value;
    const cf = document.getElementById('confPass').value;

    if (nw !== cf) return toast('New passwords do not match', 'danger');

    const btn = e.target.querySelector('button');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="kiq-spinner"></span> Changing...';

    try {
        const res = await fetch(`${API}/api/settings/password`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ current_password: curr, new_password: nw }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);

        e.target.reset();
        toast('Password changed successfully');
    } catch (err) {
        toast(err.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
    }
});

// ============================================================
// INIT
// ============================================================
loadProfile();
loadStats();
// ============================================================
// WORKER STATUS
// ============================================================
async function loadWorkerStatus() {
    try {
        const res = await fetch(API + '/api/worker/status', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        const el = document.getElementById('workerStatus');
        if (!el) return;

        if (!d.running) {
            el.innerHTML = '<span style="color: var(--kiq-danger-600);">● Worker not running</span>';
            return;
        }

        const nextRun = d.jobs[0]?.next_run ? new Date(d.jobs[0].next_run).toLocaleTimeString('en-IN') : 'unknown';

        el.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="color: var(--kiq-success-600); font-weight: 600;">● Running</span>
                <span style="font-size: 13px;">Auto-sync every 5 minutes</span>
            </div>
            <div style="font-size: 13px;">Next run: <strong>${nextRun}</strong></div>
        `;
    } catch (e) {
        console.error(e);
    }
}

const runBtn = document.getElementById('runWorkerBtn');
if (runBtn) {
    runBtn.addEventListener('click', async () => {
        const orig = runBtn.innerHTML;
        runBtn.disabled = true;
        runBtn.innerHTML = '<span class="kiq-spinner-dark kiq-spinner"></span> Running...';

        try {
            const res = await fetch(API + '/api/worker/run-now', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
            });
            const d = await res.json();
            toast(`Synced ${d.synced} integrations, ${d.failed} failed`);
            loadWorkerStatus();
loadEmailPrefs();
        } catch (e) {
            toast('Worker run failed', 'danger');
        } finally {
            runBtn.disabled = false;
            runBtn.innerHTML = orig;
        }
    });

    loadWorkerStatus();
loadEmailPrefs();
}
// ============================================================
// THEME PICKER
// ============================================================
document.querySelectorAll('.theme-pick').forEach(btn => {
    btn.addEventListener('click', () => {
        const theme = btn.dataset.theme;
        localStorage.setItem('kiq-theme', theme);

        if (theme === 'system') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        } else {
            document.documentElement.setAttribute('data-theme', theme);
        }

        window.dispatchEvent(new CustomEvent('kiq:theme-changed', { detail: { theme } }));
        markActiveTheme();
        toast(`Theme set to ${theme}`);
    });
});

function markActiveTheme() {
    const current = localStorage.getItem('kiq-theme') || 'system';
    document.querySelectorAll('.theme-pick').forEach(b => {
        const active = b.dataset.theme === current;
        b.classList.toggle('kiq-btn-primary', active);
        b.classList.toggle('kiq-btn-secondary', !active);
    });
}

markActiveTheme();

// ============================================================
// EMAIL PREFERENCES
// ============================================================
async function loadEmailPrefs() {
    const el = document.getElementById('emailPrefs');
    if (!el) return;

    try {
        const res = await fetch(API + '/api/emails/preferences', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const prefs = await res.json();

        const items = [
            { key: 'welcome_email', label: 'Welcome emails', desc: 'Account tips and setup guides', icon: 'fa-envelope' },
            { key: 'payment_receipts', label: 'Payment receipts', desc: 'Invoice and subscription confirmations', icon: 'fa-receipt' },
            { key: 'weekly_digest', label: 'Weekly digest', desc: 'Sales summary every Monday', icon: 'fa-chart-line' },
            { key: 'sync_alerts', label: 'Sync alerts', desc: 'When integrations fail', icon: 'fa-triangle-exclamation' },
            { key: 'marketing', label: 'Marketing emails', desc: 'Product updates and tips', icon: 'fa-bullhorn' },
        ];

        el.innerHTML = items.map(it => `
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid var(--kiq-border);">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 36px; height: 36px; border-radius: 8px; background: var(--kiq-brand-50); color: var(--kiq-brand-600); display: flex; align-items: center; justify-content: center;">
                        <i class="fa-solid ${it.icon}"></i>
                    </div>
                    <div>
                        <div style="font-weight: 500; font-size: 14px;">${it.label}</div>
                        <div style="font-size: 12px; color: var(--kiq-text-muted);">${it.desc}</div>
                    </div>
                </div>
                <label style="cursor: pointer; display: flex; align-items: center;">
                    <input type="checkbox" data-pref="${it.key}" ${prefs[it.key] ? 'checked' : ''} style="width: 20px; height: 20px; accent-color: var(--kiq-brand-600); cursor: pointer;">
                </label>
            </div>
        `).join('');

        // Add save button
        el.innerHTML += `
            <button class="kiq-btn kiq-btn-primary kiq-mt-4" id="savePrefsBtn">
                <i class="fa-solid fa-save"></i> Save Preferences
            </button>
        `;

        document.getElementById('savePrefsBtn').addEventListener('click', saveEmailPrefs);
    } catch (e) {
        console.error(e);
    }
}

async function saveEmailPrefs() {
    const btn = document.getElementById('savePrefsBtn');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="kiq-spinner"></span> Saving...';

    const prefs = {};
    document.querySelectorAll('[data-pref]').forEach(cb => {
        prefs[cb.dataset.pref] = cb.checked;
    });

    try {
        const res = await fetch(API + '/api/emails/preferences', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(prefs),
        });
        if (!res.ok) throw new Error('Failed');
        toast('Email preferences saved');
    } catch (e) {
        toast(e.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
    }
}
