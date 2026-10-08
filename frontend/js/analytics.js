/* KitchenIQ — Analytics JS */
const API = window.API_URL;
const token = localStorage.getItem('token');

if (!token) window.location.href = 'login.html';

// User info
try {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const kitchen = JSON.parse(localStorage.getItem('kitchen') || '{}');
    const name = user.full_name || user.email || 'User';
    document.getElementById('userName').textContent = name;
    document.getElementById('userAvatar').textContent =
        name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
    document.getElementById('kitchenLabel').textContent = kitchen.name || 'Detailed business insights';
} catch (e) {}

document.getElementById('logoutBtn').addEventListener('click', (e) => {
    e.preventDefault();
    localStorage.clear();
    window.location.href = 'login.html';
});

// Formatters
function fmtINR(n) { return '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
function fmtINRShort(n) {
    n = Number(n || 0);
    if (n >= 10000000) return '₹' + (n / 10000000).toFixed(2) + 'Cr';
    if (n >= 100000) return '₹' + (n / 100000).toFixed(2) + 'L';
    if (n >= 1000) return '₹' + (n / 1000).toFixed(1) + 'k';
    return '₹' + n;
}

// Chart defaults
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#64748b';

let dishesChart = null, qtyChart = null, hoursChart = null;

// ============================================================
// TAB SWITCHING
// ============================================================
document.querySelectorAll('.kiq-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.kiq-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.kiq-tab-content').forEach(c => c.style.display = 'none');
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).style.display = 'block';
    });
});

// ============================================================
// LOAD DISHES
// ============================================================
async function loadDishes() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/analytics/dishes?days=${days}&limit=15`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        if (!data.length) {
            document.getElementById('dishesTable').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No dishes yet. Upload CSV first.</p>';
            return;
        }

        // Revenue chart
        const top10 = data.slice(0, 10);
        if (dishesChart) dishesChart.destroy();
        dishesChart = new Chart(document.getElementById('dishesChart'), {
            type: 'bar',
            data: {
                labels: top10.map(d => d.name),
                datasets: [{
                    label: 'Revenue',
                    data: top10.map(d => d.revenue),
                    backgroundColor: '#3b82f6',
                    borderRadius: 4,
                }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (c) => ' ' + fmtINRShort(c.raw) } },
                },
                scales: {
                    x: { beginAtZero: true, ticks: { callback: fmtINRShort }, grid: { color: '#f1f5f9' } },
                    y: { grid: { display: false }, ticks: { font: { size: 11 } } },
                },
            },
        });

        // Quantity chart
        if (qtyChart) qtyChart.destroy();
        qtyChart = new Chart(document.getElementById('qtyChart'), {
            type: 'bar',
            data: {
                labels: top10.map(d => d.name),
                datasets: [{
                    label: 'Quantity Sold',
                    data: top10.map(d => d.quantity),
                    backgroundColor: '#10b981',
                    borderRadius: 4,
                }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                    y: { grid: { display: false }, ticks: { font: { size: 11 } } },
                },
            },
        });

        // Table
        document.getElementById('dishesTable').innerHTML = `
            <table style="width: 100%; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Dish</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Orders</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Qty</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Revenue</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Margin</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(d => `
                        <tr style="border-bottom: 1px solid var(--kiq-border);">
                            <td style="padding: 12px 0; font-weight: 500;">${d.name}</td>
                            <td style="padding: 12px 0; text-align: right;">${d.orders}</td>
                            <td style="padding: 12px 0; text-align: right;">${d.quantity}</td>
                            <td style="padding: 12px 0; text-align: right; font-weight: 600;">${fmtINR(d.revenue)}</td>
                            <td style="padding: 12px 0; text-align: right;">
                                <span class="kiq-badge kiq-badge-${d.margin_pct > 30 ? 'success' : d.margin_pct > 15 ? 'warning' : 'danger'}">${d.margin_pct}%</span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;

    } catch (err) {
        console.error('Dishes load failed:', err);
    }
}

// ============================================================
// LOAD PEAK HOURS
// ============================================================
async function loadHours() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/analytics/peak-hours?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        const peak = data.reduce((max, h) => h.orders > max.orders ? h : max, { orders: 0, revenue: 0, label: '—' });
        const peakRevHour = data.reduce((max, h) => h.revenue > max.revenue ? h : max, { revenue: 0, label: '—' });

        document.getElementById('peakHour').textContent = peak.label;
        document.getElementById('peakHourOrders').textContent = peak.orders + ' orders';
        document.getElementById('peakRev').textContent = fmtINR(peakRevHour.revenue);

        if (hoursChart) hoursChart.destroy();
        hoursChart = new Chart(document.getElementById('hoursChart'), {
            type: 'bar',
            data: {
                labels: data.map(h => h.label),
                datasets: [{
                    label: 'Orders',
                    data: data.map(h => h.orders),
                    backgroundColor: '#3b82f6',
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                    x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 0 } },
                },
            },
        });

    } catch (err) {
        console.error('Hours load failed:', err);
    }
}

// ============================================================
// LOAD CANCELLATIONS
// ============================================================
async function loadCancellations() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/analytics/cancellations?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        document.getElementById('cancelRate').textContent = data.overall.rate_pct + '%';
        document.getElementById('cancelCount').textContent = data.overall.cancelled;
        document.getElementById('lostRev').textContent = fmtINR(data.overall.lost_revenue);

        if (!data.by_platform.length) {
            document.getElementById('cancelPlatforms').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No data</p>';
            return;
        }

        document.getElementById('cancelPlatforms').innerHTML = `
            <table style="width: 100%; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Platform</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Cancelled</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Total</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Rate</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.by_platform.map(p => `
                        <tr style="border-bottom: 1px solid var(--kiq-border);">
                            <td style="padding: 12px 0; font-weight: 500;">${p.platform}</td>
                            <td style="padding: 12px 0; text-align: right;">${p.cancelled}</td>
                            <td style="padding: 12px 0; text-align: right;">${p.total}</td>
                            <td style="padding: 12px 0; text-align: right;">
                                <span class="kiq-badge kiq-badge-${p.rate_pct > 15 ? 'danger' : p.rate_pct > 5 ? 'warning' : 'success'}">${p.rate_pct}%</span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;

    } catch (err) {
        console.error('Cancellations load failed:', err);
    }
}

// ============================================================
// MAIN
// ============================================================
function loadAll() {
    loadDishes();
    loadHours();
    loadCancellations();
}

document.getElementById('periodSelect').addEventListener('change', loadAll);

loadAll();