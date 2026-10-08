/* KitchenIQ — Dashboard JS */
const API = window.API_URL;
const token = localStorage.getItem('token');

if (!token) window.location.href = 'login.html';

// Show user
try {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const kitchen = JSON.parse(localStorage.getItem('kitchen') || '{}');
    const name = user.full_name || user.email || 'User';
    document.getElementById('userName').textContent = name;
    document.getElementById('userAvatar').textContent =
        name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
    document.getElementById('kitchenLabel').textContent = kitchen.name || '—';
} catch (e) {}

// Logout
document.getElementById('logoutBtn').addEventListener('click', (e) => {
    e.preventDefault();
    localStorage.clear();
    window.location.href = 'login.html';
});

// Formatters
function fmtINR(n) {
    return '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}
function fmtINRShort(n) {
    n = Number(n || 0);
    if (n >= 10000000) return '₹' + (n / 10000000).toFixed(2) + 'Cr';
    if (n >= 100000) return '₹' + (n / 100000).toFixed(2) + 'L';
    if (n >= 1000) return '₹' + (n / 1000).toFixed(1) + 'k';
    return '₹' + n;
}
function fmtPct(p) {
    const n = Number(p) || 0;
    const sign = n > 0 ? '+' : '';
    return sign + n.toFixed(1) + '%';
}

// Charts
let trendChart = null;
let platformChart = null;

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#64748b';

function renderTrendChart(data) {
    const ctx = document.getElementById('trendChart');
    if (trendChart) trendChart.destroy();

    const revGrad = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    revGrad.addColorStop(0, 'rgba(59, 130, 246, 0.2)');
    revGrad.addColorStop(1, 'rgba(59, 130, 246, 0)');

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: data.revenue,
                    borderColor: '#3b82f6',
                    backgroundColor: revGrad,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3,
                },
                {
                    label: 'Profit',
                    data: data.profit,
                    borderColor: '#10b981',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', align: 'end', labels: { usePointStyle: true, boxWidth: 6, font: { size: 11 } } },
                tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${fmtINRShort(c.raw)}` } },
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { callback: fmtINRShort, maxTicksLimit: 6 } },
                x: { grid: { display: false } },
            },
        },
    });
}

function renderPlatformChart(data) {
    const ctx = document.getElementById('platformChart');
    if (platformChart) platformChart.destroy();

    platformChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                { label: 'Gross Revenue', data: data.gross_revenue, backgroundColor: '#3b82f6', borderRadius: 4, barPercentage: 0.6 },
                { label: 'Commission', data: data.commission, backgroundColor: '#ef4444', borderRadius: 4, barPercentage: 0.6 },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', align: 'end', labels: { usePointStyle: true, boxWidth: 6, font: { size: 11 } } },
                tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${fmtINRShort(c.raw)}` } },
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { callback: fmtINRShort, maxTicksLimit: 6 } },
                x: { grid: { display: false } },
            },
        },
    });
}

function renderOrders(orders) {
    const el = document.getElementById('ordersTable');
    if (!orders || orders.length === 0) {
        el.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--kiq-text-muted);">
                <i class="fa-regular fa-inbox" style="font-size: 32px;"></i>
                <p style="margin-top: 12px;">No orders yet. Upload a CSV to get started.</p>
                <a href="upload.html" class="kiq-btn kiq-btn-primary" style="margin-top: 16px; display: inline-flex;">
                    <i class="fa-solid fa-cloud-arrow-up"></i> Upload CSV
                </a>
            </div>`;
        return;
    }

    const statusColor = {
        delivered: 'success',
        pending: 'warning',
        preparing: 'warning',
        cancelled: 'danger',
    };

    el.innerHTML = `
        <table style="width: 100%; font-size: 14px; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 1px solid var(--kiq-border);">
                    <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Order</th>
                    <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Customer</th>
                    <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Platform</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Amount</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Status</th>
                </tr>
            </thead>
            <tbody>
                ${orders.map(o => `
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <td style="padding: 12px 0; font-weight: 500;">${o.id}</td>
                        <td style="padding: 12px 0;">${o.customer}</td>
                        <td style="padding: 12px 0;">${o.platform}</td>
                        <td style="padding: 12px 0; text-align: right; font-weight: 600;">${fmtINR(o.amount)}</td>
                        <td style="padding: 12px 0; text-align: right;">
                            <span class="kiq-badge kiq-badge-${statusColor[o.status] || 'gray'}">${o.status}</span>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
}

async function loadDashboard() {
    const days = document.getElementById('periodSelect').value;

    try {
        const res = await fetch(API + `/api/dashboard/summary?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to load');

        const k = data.kpis;
        document.getElementById('kpiRevenue').textContent = fmtINR(k.total_revenue);
        document.getElementById('kpiOrders').textContent = k.total_orders;
        document.getElementById('kpiProfit').textContent = fmtINR(k.net_profit);
        document.getElementById('kpiAov').textContent = fmtINR(k.avg_order_value);
        document.getElementById('kpiCancellation').textContent = k.cancellation_rate + '%';

        // Revenue trend badge
        const rTrend = document.getElementById('kpiRevenueTrend');
        const rPct = k.revenue_growth_pct;
        rTrend.className = 'kiq-kpi-trend ' + (rPct > 0 ? 'up' : rPct < 0 ? 'down' : 'flat');
        rTrend.innerHTML = `<i class="fa-solid fa-arrow-trend-${rPct > 0 ? 'up' : rPct < 0 ? 'down' : 'minus'}"></i> ${fmtPct(rPct)}`;

        // Orders trend badge
        const oTrend = document.getElementById('kpiOrdersTrend');
        const oPct = k.orders_growth_pct;
        oTrend.className = 'kiq-kpi-trend ' + (oPct > 0 ? 'up' : oPct < 0 ? 'down' : 'flat');
        oTrend.innerHTML = `<i class="fa-solid fa-arrow-trend-${oPct > 0 ? 'up' : oPct < 0 ? 'down' : 'minus'}"></i> ${fmtPct(oPct)}`;

        // Charts
        if (data.trend.labels.length) renderTrendChart(data.trend);
        if (data.platforms.labels.length) renderPlatformChart(data.platforms);

        // Recent orders
        const ordRes = await fetch(API + '/api/dashboard/recent-orders?limit=10', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const orders = await ordRes.json();
        renderOrders(orders);

    } catch (err) {
        console.error('Dashboard load failed:', err);
    }
}

document.getElementById('periodSelect').addEventListener('change', loadDashboard);

loadDashboard();