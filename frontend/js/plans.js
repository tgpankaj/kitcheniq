/* KitchenIQ — Plans JS */
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

let isYearly = false;
let currentPlanId = null;
let allPlans = [];

function toast(msg, type = 'success') {
    const colors = { success: '#10b981', danger: '#ef4444', info: '#3b82f6' };
    const el = document.createElement('div');
    el.style.cssText = `position: fixed; top: 20px; right: 20px; z-index: 99999; background: ${colors[type]}; color: white; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; box-shadow: 0 10px 40px rgba(0,0,0,0.15); transition: all 0.3s; transform: translateX(100%); opacity: 0;`;
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(() => { el.style.transform = 'translateX(0)'; el.style.opacity = '1'; });
    setTimeout(() => { el.style.transform = 'translateX(100%)'; el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3000);
}

// ============================================================
// LOAD CURRENT PLAN
// ============================================================
async function loadCurrent() {
    try {
        const res = await fetch(API + '/api/plans/current', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        currentPlanId = d.plan.id;
        document.getElementById('currentPlanName').textContent = d.plan.name;
        document.getElementById('currentPlanDesc').textContent = d.plan.features[0];
        document.getElementById('currentPlanExpiry').textContent =
            d.expires_at ? 'Renews on ' + new Date(d.expires_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Free forever';
    } catch (e) { console.error(e); }
}

// ============================================================
// LOAD USAGE
// ============================================================
async function loadUsage() {
    try {
        const res = await fetch(API + '/api/plans/usage', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        const items = [
            { key: 'orders', label: 'Orders this month', icon: 'fa-receipt' },
            { key: 'kitchens', label: 'Kitchens', icon: 'fa-store' },
            { key: 'team_members', label: 'Team members', icon: 'fa-users' },
            { key: 'integrations', label: 'Integrations', icon: 'fa-plug' },
        ];

        document.getElementById('usageStats').innerHTML = items.map(it => {
            const u = d[it.key];
            const limitLabel = u.limit === -1 ? '∞' : u.limit;
            const fillColor = u.pct >= 90 ? '#fca5a5' : u.pct >= 75 ? '#fcd34d' : '#6ee7b7';
            return `
                <div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; opacity: 0.9;">
                        <span><i class="fa-solid ${it.icon}" style="margin-right: 6px;"></i>${it.label}</span>
                        <span><strong>${u.used}</strong> / ${limitLabel}</span>
                    </div>
                    <div class="usage-bar" style="background: rgba(255,255,255,0.15); margin-top: 6px;">
                        <div class="usage-fill" style="width: ${u.limit === -1 ? 100 : u.pct}%; background: ${fillLabelColor(u.pct, u.limit)};"></div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) { console.error(e); }
}

function fillLabelColor(pct, limit) {
    if (limit === -1) return '#6ee7b7';
    if (pct >= 90) return '#fca5a5';
    if (pct >= 75) return '#fcd34d';
    return '#6ee7b7';
}

// ============================================================
// LOAD PLANS
// ============================================================
async function loadPlans() {
    try {
        const res = await fetch(API + '/api/plans/');
        allPlans = await res.json();
        renderPlans();
    } catch (e) { console.error(e); }
}

function renderPlans() {
    const grid = document.getElementById('plansGrid');

    grid.innerHTML = allPlans.map(p => {
        const isCurrent = p.id === currentPlanId;
        const price = isYearly ? p.price_yearly : p.price;
        const period = p.price === 0 ? '' : (isYearly ? '/year' : '/month');

        let cardClass = 'plan-card';
        if (p.popular) cardClass += ' popular';
        if (isCurrent) cardClass += ' current';

        let badge = '';
        if (isCurrent) badge = '<span class="plan-badge-current">✓ Current Plan</span>';
        else if (p.popular) badge = '<span class="plan-badge-popular">Most Popular</span>';

        return `
            <div class="${cardClass}">
                ${badge}
                <div class="plan-name">${p.name}</div>
                <div class="plan-price">₹${price.toLocaleString('en-IN')}</div>
                <div class="plan-price-sub">${period || 'forever free'}</div>

                <ul class="plan-features">
                    ${p.features.map(f => `<li><i class="fa-solid fa-check"></i><span>${f}</span></li>`).join('')}
                </ul>

                ${isCurrent
                    ? `<button class="kiq-btn kiq-btn-secondary kiq-btn-block" disabled>Current Plan</button>`
                    : `<button class="kiq-btn kiq-btn-primary kiq-btn-block" onclick="changePlan('${p.id}')">
                        ${p.price === 0 ? 'Downgrade' : (currentPlanId === 'free' ? 'Upgrade' : 'Switch')}
                    </button>`
                }
            </div>
        `;
    }).join('');
}

// ============================================================
// CHANGE PLAN
// ============================================================
window.changePlan = async function(planId) {
    const plan = allPlans.find(p => p.id === planId);
    if (!plan) return;

    // Free plan — instant downgrade
    if (plan.price === 0) {
        if (!confirm(`Switch to ${plan.name} plan?`)) return;
        return await switchPlanDirect(planId, plan.name);
    }

    // Paid plan — initiate payment
    await window.initiatePayment(planId, plan.name, plan.price);
};


async function switchPlanDirect(planId, planName) {
    try {
        const res = await fetch(API + '/api/plans/change', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ plan: planId }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);
        toast(`Switched to ${planName}`, 'success');
        setTimeout(() => window.location.reload(), 1200);
    } catch (e) {
        toast(e.message, 'danger');
    }
}

// ============================================================
// BILLING TOGGLE
// ============================================================
document.getElementById('billingToggle').addEventListener('click', () => {
    isYearly = !isYearly;

    const knob = document.querySelector('#billingToggle div');
    knob.style.left = isYearly ? '25px' : '3px';

    document.getElementById('monthlyLabel').style.color = isYearly ? 'var(--kiq-text-muted)' : 'var(--kiq-text)';
    document.getElementById('monthlyLabel').style.fontWeight = isYearly ? '500' : '600';
    document.getElementById('yearlyLabel').style.color = isYearly ? 'var(--kiq-text)' : 'var(--kiq-text-muted)';
    document.getElementById('yearlyLabel').style.fontWeight = isYearly ? '600' : '500';

    renderPlans();
});

// ============================================================
// INIT
// ============================================================
async function init() {
    await loadCurrent();
    await loadPlans();
    loadUsage();
    loadPaymentHistory();
}

init();


// ============================================================
// PAYMENT HISTORY
// ============================================================
async function loadPaymentHistory() {
    const el = document.getElementById('paymentHistory');
    if (!el) return;

    try {
        const res = await fetch(API + '/api/payments/history', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const rows = await res.json();

        if (!rows.length) {
            el.innerHTML = '<p style="text-align:center; padding: 20px; color: var(--kiq-text-muted);">No payment history yet.</p>';
            return;
        }

        el.innerHTML = `
            <table style="width: 100%; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Date</th>
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Plan</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Amount</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(r => `
                        <tr style="border-bottom: 1px solid var(--kiq-border);">
                            <td style="padding: 12px 0; font-size: 13px;">${r.created_at ? r.created_at.split(' ')[0] : '—'}</td>
                            <td style="padding: 12px 0; font-weight: 500;">${r.plan.charAt(0).toUpperCase() + r.plan.slice(1)}</td>
                            <td style="padding: 12px 0; text-align: right; font-weight: 600;">₹${Number(r.amount).toLocaleString('en-IN')}</td>
                            <td style="padding: 12px 0; text-align: right;">
                                <span class="kiq-badge kiq-badge-${r.status === 'active' ? 'success' : r.status === 'pending' ? 'warning' : 'gray'}">
                                    ${r.status}
                                </span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    } catch (e) {
        console.error(e);
    }
}
