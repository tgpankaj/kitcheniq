/* KitchenIQ — Live Orders JS */
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

function fmtINR(n) { return '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }

const STATUS_META = {
    pending:   { label: 'Pending',   color: '#94a3b8', icon: 'fa-clock' },
    preparing: { label: 'Preparing', color: '#f59e0b', icon: 'fa-fire' },
    ready:     { label: 'Ready',     color: '#3b82f6', icon: 'fa-bell-concierge' },
    delivered: { label: 'Delivered', color: '#10b981', icon: 'fa-circle-check' },
    cancelled: { label: 'Cancelled', color: '#ef4444', icon: 'fa-circle-xmark' },
};

const PLATFORM_COLORS = {
    'Zomato': '#e23744',
    'Swiggy': '#fc8019',
    'Manual': '#64748b',
    'Pos': '#4f46e5',
    'Website': '#0ea5e9',
};

let currentFilter = '';

// ============================================================
// LOAD SUMMARY
// ============================================================
async function loadSummary() {
    try {
        const res = await fetch(API + '/api/live/summary', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        document.getElementById('kpiPreparing').textContent = d.preparing;
        document.getElementById('kpiReady').textContent = d.ready;
        document.getElementById('kpiDelivered').textContent = d.delivered;
        document.getElementById('kpiCancelled').textContent = d.cancelled;
    } catch (e) { console.error(e); }
}

// ============================================================
// LOAD PERFORMANCE
// ============================================================
async function loadPerformance() {
    try {
        const res = await fetch(API + '/api/live/performance', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        // Note: prep/delivery times not tracked in current schema
        document.getElementById('perfPrep').textContent = '—';
        document.getElementById('perfDelivery').textContent = '—';
        document.getElementById('perfOnTime').textContent = (d.on_time_pct || 100) + '%';
        document.getElementById('perfLastHour').textContent = d.last_hour_orders;

        const onTimeEl = document.getElementById('perfOnTime');
        onTimeEl.style.color = d.on_time_pct >= 90 ? 'var(--kiq-success-600)'
                             : d.on_time_pct >= 75 ? 'var(--kiq-warning-600)'
                             : 'var(--kiq-danger-600)';
    } catch (e) { console.error(e); }
}

// ============================================================
// LOAD ORDERS
// ============================================================
async function loadOrders() {
    let url = API + '/api/live/orders?limit=50';
    if (currentFilter) url += '&status=' + currentFilter;

    try {
        const res = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const orders = await res.json();

        document.getElementById('orderCount').textContent = `${orders.length} orders`;

        const grid = document.getElementById('ordersGrid');

        if (!orders.length) {
            grid.innerHTML = `
                <div class="kiq-card" style="text-align: center; padding: 60px 20px;">
                    <i class="fa-solid fa-inbox" style="font-size: 40px; color: var(--kiq-text-subtle); margin-bottom: 12px;"></i>
                    <h3 style="font-size: 16px; margin-bottom: 4px;">No orders ${currentFilter ? 'with this status' : 'today'}</h3>
                    <p style="color: var(--kiq-text-muted); font-size: 14px;">Orders will appear here as they come in.</p>
                </div>`;
            return;
        }

        grid.innerHTML = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px;">' +
            orders.map(o => {
                const meta = STATUS_META[o.status] || STATUS_META.pending;
                const platformColor = PLATFORM_COLORS[o.platform] || '#64748b';
                const isUrgent = o.minutes_ago > 30 && o.status !== 'delivered' && o.status !== 'cancelled';

                return `
                    <div class="order-card ${o.status}">
                        <div class="order-time-badge ${isUrgent ? 'urgent' : ''}">
                            ${o.minutes_ago}m ago
                        </div>

                        <div style="margin-bottom: 10px;">
                            <div style="font-weight: 700; font-size: 15px; color: var(--kiq-text);">${o.display_id}</div>
                            <div style="font-size: 11px; color: var(--kiq-text-muted); margin-top: 2px;">
                                <span style="background: ${platformColor}; color: white; padding: 2px 6px; border-radius: 3px; font-weight: 600;">${o.platform}</span>
                                <span style="margin-left: 6px;">${o.time}</span>
                            </div>
                        </div>

                        <div style="font-size: 13px; color: var(--kiq-text); margin-bottom: 6px;">
                            <i class="fa-solid fa-user" style="color: var(--kiq-text-muted); width: 14px;"></i>
                            ${o.customer}
                        </div>

                        <div style="font-size: 12px; color: var(--kiq-text-muted); margin-bottom: 12px; min-height: 32px; line-height: 1.4;">
                            ${o.items}
                        </div>

                        <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid var(--kiq-border);">
                            <div style="font-weight: 700; font-size: 16px;">${fmtINR(o.amount)}</div>
                            <span class="kiq-badge" style="background: ${meta.color}20; color: ${meta.color};">
                                <i class="fa-solid ${meta.icon}"></i> ${meta.label}
                            </span>
                        </div>

                        ${o.status !== 'delivered' && o.status !== 'cancelled' ? `
                            <div style="display: flex; gap: 6px; margin-top: 10px;">
                                ${o.status !== 'preparing' ? `<button class="kiq-btn kiq-btn-secondary kiq-btn-sm" onclick="setStatus(${o.id}, 'preparing')" style="flex: 1;">🔥 Prep</button>` : ''}
                                ${o.status !== 'ready' ? `<button class="kiq-btn kiq-btn-secondary kiq-btn-sm" onclick="setStatus(${o.id}, 'ready')" style="flex: 1;">✅ Ready</button>` : ''}
                                ${o.status !== 'delivered' ? `<button class="kiq-btn kiq-btn-primary kiq-btn-sm" onclick="setStatus(${o.id}, 'delivered')" style="flex: 1;">🚀 Done</button>` : ''}
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('') + '</div>';

    } catch (e) { console.error(e); }
}

// ============================================================
// ACTIONS
// ============================================================
window.setStatus = async function(orderId, status) {
    try {
        const res = await fetch(`${API}/api/live/orders/${orderId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ status }),
        });
        if (!res.ok) throw new Error((await res.json()).error);

        if (window.showToast) window.showToast(`Order marked as ${status}`, 'success');
        loadAll();
    } catch (e) {
        if (window.showToast) window.showToast(e.message, 'danger');
    }
};

window.filterByStatus = function(status) {
    document.getElementById('statusFilter').value = status;
    currentFilter = status;
    loadOrders();
};

// ============================================================
// INIT
// ============================================================
function loadAll() {
    loadSummary();
    loadPerformance();
    loadOrders();
}

document.getElementById('statusFilter').addEventListener('change', (e) => {
    currentFilter = e.target.value;
    loadOrders();
});

// Auto-refresh every 15 seconds
setInterval(loadAll, 15000);

loadAll();
