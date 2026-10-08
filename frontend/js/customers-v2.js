/* KitchenIQ — Customers v2 JS */
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

let segmentChart = null;
let allCustomers = [];

// ============================================================
// TAB SWITCHING
// ============================================================
document.querySelectorAll('.kiq-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.kiq-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.kiq-tab-content').forEach(c => c.style.display = 'none');
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).style.display = 'block';

        // Lazy load
        if (tab.dataset.tab === 'cohorts') loadCohorts();
        if (tab.dataset.tab === 'clv') loadCLV();
        if (tab.dataset.tab === 'churn') loadChurn();
    });
});

// ============================================================
// SEGMENTS TAB (existing functionality)
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
        document.getElementById('kpiRepeatSub').textContent = data.kpis.repeat_customers + ' repeat';
        document.getElementById('kpiLTV').textContent = fmtINR(data.kpis.avg_lifetime_value);
        document.getElementById('kpiAvgOrders').textContent = data.kpis.avg_orders_per_customer;

        const labels = data.segments.map(s => s.name);
        const counts = data.segments.map(s => s.count);
        const colors = data.segments.map(s => SEGMENT_COLORS[s.name]);

        if (segmentChart) segmentChart.destroy();
        segmentChart = new Chart(document.getElementById('segmentChart'), {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data: counts, backgroundColor: colors, borderWidth: 0 }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { usePointStyle: true, boxWidth: 8, padding: 14, font: { size: 12 } } },
                },
                cutout: '65%',
            },
        });
    } catch (e) { console.error(e); }
}

async function loadSegmentRevenue() {
    try {
        const res = await fetch(`${API}/api/customers/segment-revenue`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        document.getElementById('segmentTable').innerHTML = data.map(s => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--kiq-border);">
                <div style="flex: 1;">
                    <span class="kiq-badge kiq-badge-${SEGMENT_BADGE[s.segment]}">${s.segment}</span>
                    <span style="font-size: 12px; color: var(--kiq-text-muted); margin-left: 8px;">${s.customers} customers</span>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 600;">${fmtINR(s.revenue)}</div>
                    <div style="font-size: 11px; color: var(--kiq-text-muted);">${s.revenue_share_pct}% of total</div>
                </div>
            </div>
        `).join('') || '<p style="text-align:center; padding: 20px; color: var(--kiq-text-muted);">No data</p>';
    } catch (e) { console.error(e); }
}

async function loadCustomers() {
    const days = document.getElementById('periodSelect').value;
    const segment = document.getElementById('segmentFilter').value;
    let url = `${API}/api/customers/?days=${days}&limit=100`;
    if (segment) url += `&segment=${encodeURIComponent(segment)}`;

    try {
        const res = await fetch(url, { headers: { 'Authorization': 'Bearer ' + token } });
        allCustomers = await res.json();
        renderCustomers(allCustomers);
    } catch (e) { console.error(e); }
}

function renderCustomers(customers) {
    if (!customers.length) {
        document.getElementById('customersTable').innerHTML = '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No customers match your filter.</p>';
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
                        <td style="padding: 12px 0; text-align: right; font-size: 13px; color: var(--kiq-text-muted);">${c.recency_days}d ago</td>
                        <td style="padding: 12px 0; text-align: right;">
                            <span class="kiq-badge kiq-badge-${SEGMENT_BADGE[c.segment]}">${c.segment}</span>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
}

// ============================================================
// COHORTS TAB
// ============================================================
async function loadCohorts() {
    const months = document.getElementById('cohortMonthsSelect').value;
    try {
        const res = await fetch(`${API}/api/customers/cohorts?months=${months}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        const cohorts = data.cohorts || [];

        if (!cohorts.length) {
            document.getElementById('cohortTable').innerHTML = '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No cohort data yet. Need more order history.</p>';
            return;
        }

        // Find max offset
        let maxOffset = 0;
        cohorts.forEach(c => {
            c.retention.forEach(r => {
                if (r.offset > maxOffset) maxOffset = r.offset;
            });
        });

        // Build header
        let header = '<th style="text-align: left; padding: 10px; font-size: 11px; color: var(--kiq-text-muted); text-transform: uppercase;">Cohort</th>';
        header += '<th style="text-align: center; padding: 10px; font-size: 11px; color: var(--kiq-text-muted); text-transform: uppercase;">Size</th>';
        for (let i = 0; i <= maxOffset; i++) {
            header += `<th style="text-align: center; padding: 10px; font-size: 11px; color: var(--kiq-text-muted); text-transform: uppercase;">M+${i}</th>`;
        }

        let body = '';
        cohorts.forEach(c => {
            const cohortDate = new Date(c.cohort);
            const label = cohortDate.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' });

            body += `<tr style="border-bottom: 1px solid var(--kiq-border);">
                <td style="padding: 10px; font-weight: 500;">${label}</td>
                <td style="padding: 10px; text-align: center;">${c.total_customers}</td>`;

            for (let i = 0; i <= maxOffset; i++) {
                const r = c.retention.find(x => x.offset === i);
                if (r && r.count > 0) {
                    const color = `hsl(${Math.min(120, r.pct * 1.2)}, 70%, ${Math.max(35, 85 - r.pct / 2)}%)`;
                    body += `<td style="padding: 6px; text-align: center;">
                        <span class="cohort-cell" style="background: ${color};">${r.pct}%</span>
                    </td>`;
                } else {
                    body += `<td style="padding: 6px; text-align: center; color: var(--kiq-text-subtle);">—</td>`;
                }
            }
            body += '</tr>';
        });

        document.getElementById('cohortTable').innerHTML = `
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead><tr style="background: var(--kiq-bg-sunken);">${header}</tr></thead>
                <tbody>${body}</tbody>
            </table>
        `;

    } catch (e) { console.error(e); }
}

// ============================================================
// CLV TAB
// ============================================================
async function loadCLV() {
    try {
        const res = await fetch(`${API}/api/customers/clv`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        document.getElementById('clvLTV').textContent = fmtINR(d.avg_lifetime_value);
        document.getElementById('clvAOV').textContent = fmtINR(d.avg_order_value);
        document.getElementById('clvAvgOrders').textContent = d.avg_orders_per_customer;
        document.getElementById('clvTotal').textContent = d.total_customers;

        document.getElementById('topCustomersList').innerHTML = (d.top_customers || []).map((c, i) => `
            <div style="display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--kiq-border);">
                <div style="width: 32px; height: 32px; border-radius: 50%; background: ${i < 3 ? '#fef3c7' : 'var(--kiq-bg-sunken)'}; color: ${i < 3 ? '#b45309' : 'var(--kiq-text-muted)'}; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; margin-right: 12px;">
                    ${c.clv_rank}
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 500;">${c.name}</div>
                    <div style="font-size: 12px; color: var(--kiq-text-muted);">${c.phone} · ${c.orders} orders</div>
                </div>
                <div style="font-weight: 700; font-size: 15px;">${fmtINR(c.revenue)}</div>
            </div>
        `).join('') || '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No data</p>';

    } catch (e) { console.error(e); }
}

// ============================================================
// CHURN TAB
// ============================================================
async function loadChurn() {
    try {
        const res = await fetch(`${API}/api/customers/churn-risk`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const customers = await res.json();

        document.getElementById('churnCount').textContent = `${customers.length} at-risk customers`;

        if (!customers.length) {
            document.getElementById('churnList').innerHTML = '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">🎉 No at-risk customers! Everyone ordered recently.</p>';
            return;
        }

        document.getElementById('churnList').innerHTML = `
            <table style="width: 100%; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Customer</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Orders</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Lifetime Spend</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Last Order</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Risk</th>
                    </tr>
                </thead>
                <tbody>
                    ${customers.map(c => `
                        <tr style="border-bottom: 1px solid var(--kiq-border);">
                            <td style="padding: 12px 0;">
                                <div style="font-weight: 500;">${c.name}</div>
                                <div style="font-size: 12px; color: var(--kiq-text-muted);">${c.phone}</div>
                            </td>
                            <td style="padding: 12px 0; text-align: right;">${c.total_orders}</td>
                            <td style="padding: 12px 0; text-align: right; font-weight: 600;">${fmtINR(c.total_spent)}</td>
                            <td style="padding: 12px 0; text-align: right; font-size: 13px; color: var(--kiq-text-muted);">${c.days_since}d ago</td>
                            <td style="padding: 12px 0; text-align: right;">
                                <span class="kiq-badge kiq-badge-${c.risk_level === 'high' ? 'danger' : 'warning'}">${c.risk_level.toUpperCase()}</span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    } catch (e) { console.error(e); }
}

// ============================================================
// EVENTS
// ============================================================
document.getElementById('periodSelect').addEventListener('change', () => {
    loadSummary();
    loadCustomers();
});
document.getElementById('segmentFilter').addEventListener('change', loadCustomers);
document.getElementById('cohortMonthsSelect').addEventListener('change', loadCohorts);
document.getElementById('searchInput').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    const filtered = q ? allCustomers.filter(c => c.name.toLowerCase().includes(q) || c.phone.includes(q)) : allCustomers;
    renderCustomers(filtered);
});

// INIT
loadSummary();
loadSegmentRevenue();
loadCustomers();
