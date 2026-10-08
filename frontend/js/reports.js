/* KitchenIQ — Reports JS */
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

let dailyChart = null;

// ============================================================
// LOAD SUMMARY
// ============================================================
async function loadSummary() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/reports/summary?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();

        document.getElementById('sumRevenue').textContent = fmtINR(d.revenue);
        document.getElementById('sumProfit').textContent = fmtINR(d.profit);
        document.getElementById('sumMargin').textContent = d.margin_pct + '% margin';
        document.getElementById('sumOrders').textContent = d.orders;
        document.getElementById('sumCancelled').textContent = d.cancelled + ' cancelled';
        document.getElementById('sumAov').textContent = fmtINR(d.avg_order_value);
    } catch (e) { console.error(e); }
}

// ============================================================
// LOAD DAILY
// ============================================================
async function loadDaily() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/reports/daily?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        if (!data.length) {
            document.getElementById('dailyTable').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No data in this period.</p>';
            return;
        }

        // Sort ascending for chart
        const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date));

        // Chart
        if (dailyChart) dailyChart.destroy();
        const ctx = document.getElementById('dailyChart').getContext('2d');
        const grad = ctx.createLinearGradient(0, 0, 0, 320);
        grad.addColorStop(0, 'rgba(59, 130, 246, 0.2)');
        grad.addColorStop(1, 'rgba(59, 130, 246, 0)');

        dailyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sorted.map(d => d.date.slice(5)),
                datasets: [
                    {
                        label: 'Revenue',
                        data: sorted.map(d => d.revenue),
                        borderColor: '#3b82f6',
                        backgroundColor: grad,
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                    },
                    {
                        label: 'Profit',
                        data: sorted.map(d => d.profit),
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

        // Table (descending)
        document.getElementById('dailyTable').innerHTML = `
            <table style="width: 100%; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Date</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Orders</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Revenue</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Fees</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Profit</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Margin</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(d => {
                        const margin = d.revenue > 0 ? (d.profit / d.revenue * 100) : 0;
                        return `
                            <tr style="border-bottom: 1px solid var(--kiq-border);">
                                <td style="padding: 12px 0; font-weight: 500;">${d.date}</td>
                                <td style="padding: 12px 0; text-align: right;">${d.orders}</td>
                                <td style="padding: 12px 0; text-align: right; font-weight: 600;">${fmtINR(d.revenue)}</td>
                                <td style="padding: 12px 0; text-align: right; color: var(--kiq-danger-600);">${fmtINR(d.platform_fees)}</td>
                                <td style="padding: 12px 0; text-align: right; font-weight: 600; color: ${d.profit >= 0 ? 'var(--kiq-success-600)' : 'var(--kiq-danger-600)'};">${fmtINR(d.profit)}</td>
                                <td style="padding: 12px 0; text-align: right;">
                                    <span class="kiq-badge kiq-badge-${margin > 30 ? 'success' : margin > 15 ? 'warning' : 'danger'}">${margin.toFixed(1)}%</span>
                                </td>
                            </tr>`;
                    }).join('')}
                </tbody>
            </table>`;
    } catch (e) { console.error(e); }
}

// ============================================================
// EXPORT
// ============================================================
document.getElementById('exportBtn').addEventListener('click', async () => {
    const days = document.getElementById('periodSelect').value;
    const btn = document.getElementById('exportBtn');
    const original = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = '<span class="kiq-spinner"></span> Exporting...';

    try {
        const res = await fetch(`${API}/api/reports/export?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });

        if (!res.ok) throw new Error('Export failed');

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `kitcheniq-orders-${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        btn.innerHTML = '<i class="fa-solid fa-check"></i> Downloaded';
        setTimeout(() => {
            btn.innerHTML = original;
            btn.disabled = false;
        }, 2000);
    } catch (e) {
        alert('Export failed: ' + e.message);
        btn.innerHTML = original;
        btn.disabled = false;
    }
});


// ============================================================
// EXCEL EXPORT
// ============================================================
const excelBtn = document.getElementById('exportExcelBtn');
if (excelBtn) {
    excelBtn.addEventListener('click', async () => {
        const days = document.getElementById('periodSelect').value;
        const orig = excelBtn.innerHTML;
        excelBtn.disabled = true;
        excelBtn.innerHTML = '<span class="kiq-spinner-dark kiq-spinner"></span> Generating...';

        try {
            const res = await fetch(`${API}/api/reports/export-excel?days=${days}`, {
                headers: { 'Authorization': 'Bearer ' + token },
            });
            if (!res.ok) throw new Error('Export failed');

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `kitcheniq-report-${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            excelBtn.innerHTML = '<i class="fa-solid fa-check"></i> Done';
            setTimeout(() => { excelBtn.innerHTML = orig; excelBtn.disabled = false; }, 2000);
        } catch (e) {
            alert('Excel export failed: ' + e.message);
            excelBtn.innerHTML = orig;
            excelBtn.disabled = false;
        }
    });
}

// ============================================================
// PDF EXPORT
// ============================================================
const pdfBtn = document.getElementById('exportPdfBtn');
if (pdfBtn) {
    pdfBtn.addEventListener('click', async () => {
        const days = document.getElementById('periodSelect').value;
        const orig = pdfBtn.innerHTML;
        pdfBtn.disabled = true;
        pdfBtn.innerHTML = '<span class="kiq-spinner-dark kiq-spinner"></span> Generating...';

        try {
            const res = await fetch(`${API}/api/reports/export-pdf?days=${days}`, {
                headers: { 'Authorization': 'Bearer ' + token },
            });
            if (!res.ok) throw new Error('Export failed');

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `kitcheniq-report-${new Date().toISOString().slice(0, 10)}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            pdfBtn.innerHTML = '<i class="fa-solid fa-check"></i> Done';
            setTimeout(() => { pdfBtn.innerHTML = orig; pdfBtn.disabled = false; }, 2000);
        } catch (e) {
            alert('PDF export failed: ' + e.message);
            pdfBtn.innerHTML = orig;
            pdfBtn.disabled = false;
        }
    });
}

// ============================================================
// INIT
// ============================================================
function loadAll() {
    loadSummary();
    loadDaily();
}

document.getElementById('periodSelect').addEventListener('change', loadAll);

loadAll();