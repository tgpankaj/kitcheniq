/* KitchenIQ — Customers JS */
const API = window.API_URL;
const token = localStorage.getItem('token');

if (!token) window.location.href = 'login.html';

// User info
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

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#64748b';

let segmentChart = null;
let allCustomers = [];

// Segment colors
const SEGMENT_COLORS = {
    'VIP': '#10b981',
    'Loyal': '#3b82f6',
    'New': '#8b5cf6',
    'At Risk': '#f59e0b',
    'Lost': '#ef4444',
};

const SEGMENT_BADGE = {
    'VIP': 'success',
    'Loyal': 'brand',
    'New': 'info',
    'At Risk': 'warning',
    'Lost': 'danger',
};

// ============================================================
// LOAD SUMMARY
// ============================================================
async function loadSummary() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/customers/summary?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        document.getElementById('kpiTotal').textContent = data.kpis.total_customers;
        document.getElementById('kpiRepeat').textContent = data.kpis.repeat_rate_pct + '%';
        document.getElementById('kpiRepeatCount').textContent = data.kpis.repeat_customers + ' repeat customers';
        document.getElementById('kpiLTV').textContent = fmtINR(data.kpis.avg_lifetime_value);
        document.getElementById('kpiAvgOrders').textContent = data.kpis.avg_orders_per_customer;

        // Chart
        const labels = data.segments.map(s => s.name);
        const counts = data.segments.map(s => s.count);
        const colors = data.segments.map(s => SEGMENT_COLORS[s.name] || '#94a3b8');

        if (segmentChart) segmentChart.destroy();
        segmentChart = new Chart(document.getElementById('segmentChart'), {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { usePointStyle: true, boxWidth: 8, padding: 14, font: { size: 12 } } },
                    tooltip: {
                        callbacks: {
                            label: (c) => {
                                const total = c.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = total ? (c.raw / total * 100).toFixed(1) : 0;
                                return ` ${c.label}: ${c.raw} (${pct}%)`;
                            },
                        },
                    },
                },
                cutout: '65%',
            },
        });
    } catch (err) {
        console.error('Summary load failed:', err);
    }
}

// ============================================================
// LOAD TOP CUSTOMERS
// ============================================================
async function loadTopCustomers() {
    try {
        const res = await fetch(`${API}/api/customers/top?limit=8`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        if (!data.length) {
            document.getElementById('topCustomersList').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No customers yet.</p>';
            return;
        }

        document.getElementById('topCustomersList').innerHTML = data.map((c, i) => `
            <div style="display: flex; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--kiq-border);">
                <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--kiq-brand-100); color: var(--kiq-brand-700); display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 13px; margin-right: 12px; flex-shrink: 0;">
                    ${i + 1}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-weight: 500; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${c.name}</div>
                    <div style="font-size: 12px; color: var(--kiq-text-muted);">${c.orders} orders</div>
                </div>
                <div style="font-weight: 600; font-size: 14px;">${fmtINR(c.total_spent)}</div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Top customers load failed:', err);
    }
}

// ============================================================
// LOAD CUSTOMERS LIST
// ============================================================
async function loadCustomers() {
    const days = document.getElementById('periodSelect').value;
    const segment = document.getElementById('segmentFilter').value;

    let url = `${API}/api/customers/?days=${days}&limit=100`;
    if (segment) url += `&segment=${encodeURIComponent(segment)}`;

    try {
        const res = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        allCustomers = await res.json();
        renderCustomers(allCustomers);
    } catch (err) {
        console.error('Customers load failed:', err);
    }
}

function renderCustomers(customers) {
    if (!customers.length) {
        document.getElementById('customersTable').innerHTML =
            '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No customers match your filter.</p>';
        return;
    }

    document.getElementById('customersTable').innerHTML = `
        <table style="width: 100%; font-size: 14px;">
            <thead>
                <tr style="border-bottom: 1px solid var(--kiq-border);">
                    <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Customer</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Orders</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Total Spent</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Last Order</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Segment</th>
                </tr>
            </thead>
            <tbody>
                ${customers.map(c => `
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <td style="padding: 12px 0;">
                            <div style="font-weight: 500;">${c.name}</div>
                            <div style="font-size: 12px; color: var(--kiq-text-muted);">${c.phone}</div>
                        </td>
                        <td style="padding: 12px 0; text-align: right;">${c.orders}</td>
                        <td style="padding: 12px 0; text-align: right; font-weight: 600;">${fmtINR(c.total_spent)}</td>
                        <td style="padding: 12px 0; text-align: right; font-size: 13px; color: var(--kiq-text-muted);">
                            ${c.recency_days}d ago
                        </td>
                        <td style="padding: 12px 0; text-align: right;">
                            <span class="kiq-badge kiq-badge-${SEGMENT_BADGE[c.segment] || 'gray'}">${c.segment}</span>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
}

// ============================================================
// SEARCH
// ============================================================
document.getElementById('searchInput').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) return renderCustomers(allCustomers);
    const filtered = allCustomers.filter(c =>
        c.name.toLowerCase().includes(q) ||
        c.phone.includes(q)
    );
    renderCustomers(filtered);
});

// Events
document.getElementById('periodSelect').addEventListener('change', () => {
    loadSummary();
    loadCustomers();
});

document.getElementById('segmentFilter').addEventListener('change', loadCustomers);

// Init
loadSummary();
loadTopCustomers();
loadCustomers();