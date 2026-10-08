/* KitchenIQ — Finance JS */
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

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#64748b';

let costChart = null;

// ============================================================
// LOAD P&L
// ============================================================
async function loadPnL() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/finance/pnl?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        // KPI cards
        document.getElementById('kpiGross').textContent = fmtINR(d.gross_revenue);
        document.getElementById('kpiOrders').textContent = d.orders + ' orders';
        document.getElementById('kpiNetSales').textContent = fmtINR(d.net_sales);
        document.getElementById('kpiDiscounts').innerHTML = `− ${fmtINR(d.discounts)} (${d.discount_pct}%)`;
        document.getElementById('kpiCosts').textContent = fmtINR(d.total_costs);
        document.getElementById('kpiProfit').textContent = fmtINR(d.profit);

        // Margin badge
        const marginEl = document.getElementById('kpiMargin');
        marginEl.textContent = d.profit_margin_pct + '% margin';
        marginEl.className = 'kiq-kpi-trend ' + (d.profit_margin_pct > 20 ? 'up' : d.profit_margin_pct > 10 ? 'flat' : 'down');

        // P&L statement
        renderPnL(d);

    } catch (err) {
        console.error('P&L load failed:', err);
    }
}

function renderPnL(d) {
    const row = (label, value, opts = {}) => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: ${opts.padding || '8px 0'}; ${opts.border ? 'border-top: 1px solid var(--kiq-border); margin-top: 8px;' : ''}">
            <span style="color: ${opts.muted ? 'var(--kiq-text-muted)' : 'var(--kiq-text)'}; font-weight: ${opts.bold ? '600' : '400'}; font-size: ${opts.big ? '15px' : '14px'};">
                ${label}
            </span>
            <span style="font-weight: ${opts.bold ? '700' : '500'}; font-size: ${opts.big ? '16px' : '14px'}; color: ${opts.color || 'var(--kiq-text)'};">
                ${value}
            </span>
        </div>`;

    document.getElementById('pnlStatement').innerHTML = `
        ${row('Gross Revenue', fmtINR(d.gross_revenue), { bold: true })}
        ${row('− Discounts', fmtINR(d.discounts), { muted: true, color: 'var(--kiq-danger-600)' })}
        ${row('= Net Sales', fmtINR(d.net_sales), { bold: true, border: true, big: true, color: 'var(--kiq-brand-700)' })}

        <div style="margin-top: 20px;"></div>

        ${row('− Food Cost', fmtINR(d.food_cost) + ` (${d.food_cost_pct}%)`, { muted: true })}
        ${row('− Platform Fees', fmtINR(d.platform_fees) + ` (${d.platform_fee_pct}%)`, { muted: true })}
        ${row('− Packaging', fmtINR(d.packaging_cost) + ` (${d.packaging_pct}%)`, { muted: true })}
        ${row('= Total Costs', fmtINR(d.total_costs), { bold: true, border: true })}

        <div style="margin-top: 20px;"></div>

        <div style="padding: 16px; background: ${d.profit >= 0 ? 'var(--kiq-success-50)' : 'var(--kiq-danger-50)'}; border-radius: 8px; border: 1px solid ${d.profit >= 0 ? '#a7f3d0' : '#fecaca'};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; color: ${d.profit >= 0 ? 'var(--kiq-success-700)' : 'var(--kiq-danger-700)'}; font-size: 15px;">
                    ${d.profit >= 0 ? '✓ Net Profit' : '✗ Net Loss'}
                </span>
                <span style="font-weight: 700; font-size: 22px; color: ${d.profit >= 0 ? 'var(--kiq-success-700)' : 'var(--kiq-danger-700)'};">
                    ${fmtINR(d.profit)}
                </span>
            </div>
            <div style="font-size: 12px; color: ${d.profit >= 0 ? 'var(--kiq-success-600)' : 'var(--kiq-danger-600)'}; margin-top: 4px;">
                ${d.profit_margin_pct}% margin
            </div>
        </div>
    `;
}

// ============================================================
// LOAD COST BREAKDOWN
// ============================================================
async function loadCosts() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/finance/cost-breakdown?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        if (costChart) costChart.destroy();
        costChart = new Chart(document.getElementById('costChart'), {
            type: 'doughnut',
            data: {
                labels: d.labels,
                datasets: [{
                    data: d.values,
                    backgroundColor: ['#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6', '#ec4899'],
                    borderWidth: 0,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { usePointStyle: true, boxWidth: 8, padding: 14, font: { size: 12 } },
                    },
                    tooltip: {
                        callbacks: {
                            label: (c) => {
                                const total = c.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = total ? (c.raw / total * 100).toFixed(1) : 0;
                                return ` ${c.label}: ${fmtINR(c.raw)} (${pct}%)`;
                            },
                        },
                    },
                },
                cutout: '60%',
            },
        });
    } catch (err) {
        console.error('Cost breakdown load failed:', err);
    }
}

// ============================================================
// LOAD PLATFORMS
// ============================================================
async function loadPlatforms() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/finance/platforms?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        if (!data.length) {
            document.getElementById('platformsTable').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No platform data yet.</p>';
            return;
        }

        document.getElementById('platformsTable').innerHTML = `
            <table style="width: 100%; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Platform</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Orders</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Gross</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Fees</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Fee %</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Profit</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Margin</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(p => `
                        <tr style="border-bottom: 1px solid var(--kiq-border);">
                            <td style="padding: 12px 0; font-weight: 500;">${p.platform}</td>
                            <td style="padding: 12px 0; text-align: right;">${p.orders}</td>
                            <td style="padding: 12px 0; text-align: right; font-weight: 600;">${fmtINR(p.gross_revenue)}</td>
                            <td style="padding: 12px 0; text-align: right; color: var(--kiq-danger-600);">${fmtINR(p.platform_fees)}</td>
                            <td style="padding: 12px 0; text-align: right; font-size: 13px; color: var(--kiq-text-muted);">${p.fee_pct}%</td>
                            <td style="padding: 12px 0; text-align: right; font-weight: 600; color: ${p.profit >= 0 ? 'var(--kiq-success-600)' : 'var(--kiq-danger-600)'};">${fmtINR(p.profit)}</td>
                            <td style="padding: 12px 0; text-align: right;">
                                <span class="kiq-badge kiq-badge-${p.margin_pct > 30 ? 'success' : p.margin_pct > 15 ? 'warning' : 'danger'}">
                                    ${p.margin_pct}%
                                </span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    } catch (err) {
        console.error('Platforms load failed:', err);
    }
}

// ============================================================
// INIT
// ============================================================
function loadAll() {
    loadPnL();
    loadCosts();
    loadPlatforms();
}

document.getElementById('periodSelect').addEventListener('change', loadAll);

loadAll();