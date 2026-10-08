/* KitchenIQ — Dishes JS */
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
function fmtINRShort(n) {
    n = Number(n || 0);
    if (n >= 100000) return '₹' + (n / 100000).toFixed(1) + 'L';
    if (n >= 1000) return '₹' + (n / 1000).toFixed(1) + 'k';
    return '₹' + n;
}

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#64748b';

let matrixChart = null;
let topChart = null;
let allDishes = [];

const CLASS_COLORS = {
    'Star': '#10b981',
    'Plowhorse': '#f59e0b',
    'Puzzle': '#8b5cf6',
    'Dog': '#ef4444',
};

const CLASS_BADGE = {
    'Star': 'success',
    'Plowhorse': 'warning',
    'Puzzle': 'info',
    'Dog': 'danger',
};

// ============================================================
// LOAD DISHES
// ============================================================
async function loadDishes() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/dishes/menu-engineering?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        if (!data.dishes || !data.dishes.length) {
            document.getElementById('dishesTable').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No dishes yet. Upload CSV first.</p>';
            return;
        }

        allDishes = data.dishes;

        // KPIs
        document.getElementById('kpiStars').textContent = data.summary.stars;
        document.getElementById('kpiPlowhorses').textContent = data.summary.plowhorses;
        document.getElementById('kpiPuzzles').textContent = data.summary.puzzles;
        document.getElementById('kpiDogs').textContent = data.summary.dogs;

        // Matrix chart (scatter)
        renderMatrix(data.dishes);

        // Top dishes chart
        renderTop(data.dishes.slice(0, 10));

        // Insights
        renderInsights(data);

        // Table
        renderTable(data.dishes);

    } catch (err) {
        console.error('Dishes load failed:', err);
    }
}

// ============================================================
// MATRIX CHART
// ============================================================
function renderMatrix(dishes) {
    const ctx = document.getElementById('matrixChart');
    if (matrixChart) matrixChart.destroy();

    const avgQty = dishes.reduce((s, d) => s + d.quantity, 0) / dishes.length;
    const avgMargin = dishes.reduce((s, d) => s + d.margin_pct, 0) / dishes.length;

    const grouped = { Star: [], Plowhorse: [], Puzzle: [], Dog: [] };
    dishes.forEach(d => {
        grouped[d.classification].push({
            x: d.quantity,
            y: d.margin_pct,
            r: Math.max(6, Math.min(30, Math.sqrt(d.revenue) / 5)),
            label: d.name,
            revenue: d.revenue,
        });
    });

    const datasets = Object.keys(grouped).map(cls => ({
        label: cls,
        data: grouped[cls],
        backgroundColor: CLASS_COLORS[cls] + '80',
        borderColor: CLASS_COLORS[cls],
        borderWidth: 2,
    }));

    matrixChart = new Chart(ctx, {
        type: 'bubble',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', align: 'end', labels: { usePointStyle: true, boxWidth: 8, font: { size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: (c) => {
                            const d = c.raw;
                            return [
                                ` ${d.label}`,
                                ` Qty: ${d.x}`,
                                ` Margin: ${d.y}%`,
                                ` Revenue: ${fmtINR(d.revenue)}`,
                            ];
                        },
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Quantity Sold', font: { size: 11 } },
                    grid: { color: '#f1f5f9' },
                },
                y: {
                    title: { display: true, text: 'Margin %', font: { size: 11 } },
                    grid: { color: '#f1f5f9' },
                    ticks: { callback: (v) => v + '%' },
                },
            },
            animation: {
                onComplete: function() {
                    // Draw quadrant lines
                    const chart = this;
                    const ctx = chart.ctx;
                    ctx.save();
                    ctx.strokeStyle = '#cbd5e1';
                    ctx.setLineDash([4, 4]);
                    ctx.lineWidth = 1;

                    const xScale = chart.scales.x;
                    const yScale = chart.scales.y;
                    const avgX = xScale.getPixelForValue(avgQty);
                    const avgY = yScale.getPixelForValue(avgMargin);

                    ctx.beginPath();
                    ctx.moveTo(avgX, chart.chartArea.top);
                    ctx.lineTo(avgX, chart.chartArea.bottom);
                    ctx.stroke();

                    ctx.beginPath();
                    ctx.moveTo(chart.chartArea.left, avgY);
                    ctx.lineTo(chart.chartArea.right, avgY);
                    ctx.stroke();

                    ctx.restore();
                },
            },
        },
    });
}

// ============================================================
// TOP DISHES CHART
// ============================================================
function renderTop(dishes) {
    const ctx = document.getElementById('topDishesChart');
    if (topChart) topChart.destroy();

    topChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dishes.map(d => d.name),
            datasets: [{
                label: 'Revenue',
                data: dishes.map(d => d.revenue),
                backgroundColor: dishes.map(d => CLASS_COLORS[d.classification] + 'cc'),
                borderRadius: 4,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (c) => ' ' + fmtINR(c.raw) } },
            },
            scales: {
                x: { beginAtZero: true, ticks: { callback: fmtINRShort }, grid: { color: '#f1f5f9' } },
                y: { grid: { display: false }, ticks: { font: { size: 11 } } },
            },
        },
    });
}

// ============================================================
// INSIGHTS
// ============================================================
function renderInsights(data) {
    const s = data.summary;
    const best = data.dishes.reduce((a, b) => a.revenue > b.revenue ? a : b);
    const worst = data.dishes.reduce((a, b) => a.margin_pct < b.margin_pct ? a : b);

    document.getElementById('insightsBox').innerHTML = `
        <div style="padding: 12px 0; border-bottom: 1px solid var(--kiq-border);">
            <div style="font-weight: 600; margin-bottom: 4px;">
                <i class="fa-solid fa-fire" style="color: #ef4444; margin-right: 8px;"></i>
                Best Seller
            </div>
            <p style="font-size: 13px; color: var(--kiq-text-muted);">
                <strong>${best.name}</strong> — ${fmtINR(best.revenue)} revenue
            </p>
        </div>
        <div style="padding: 12px 0; border-bottom: 1px solid var(--kiq-border);">
            <div style="font-weight: 600; margin-bottom: 4px;">
                <i class="fa-solid fa-triangle-exclamation" style="color: #f59e0b; margin-right: 8px;"></i>
                Lowest Margin
            </div>
            <p style="font-size: 13px; color: var(--kiq-text-muted);">
                <strong>${worst.name}</strong> — only ${worst.margin_pct}% margin
            </p>
        </div>
        <div style="padding: 12px 0; border-bottom: 1px solid var(--kiq-border);">
            <div style="font-weight: 600; margin-bottom: 4px;">
                <i class="fa-solid fa-star" style="color: #10b981; margin-right: 8px;"></i>
                Star Performers
            </div>
            <p style="font-size: 13px; color: var(--kiq-text-muted);">
                <strong>${s.stars}</strong> dishes are killing it (high volume + high margin)
            </p>
        </div>
        <div style="padding: 12px 0;">
            <div style="font-weight: 600; margin-bottom: 4px;">
                <i class="fa-solid fa-lightbulb" style="color: #8b5cf6; margin-right: 8px;"></i>
                Quick Wins
            </div>
            <p style="font-size: 13px; color: var(--kiq-text-muted);">
                <strong>${s.puzzles}</strong> dishes have great margin but low sales. Promote them!
            </p>
        </div>
    `;
}

// ============================================================
// TABLE
// ============================================================
function renderTable(dishes) {
    if (!dishes.length) {
        document.getElementById('dishesTable').innerHTML =
            '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No dishes</p>';
        return;
    }

    document.getElementById('dishesTable').innerHTML = `
        <table style="width: 100%; font-size: 14px;">
            <thead>
                <tr style="border-bottom: 1px solid var(--kiq-border);">
                    <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Dish</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Orders</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Qty</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Revenue</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Margin</th>
                    <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Class</th>
                </tr>
            </thead>
            <tbody>
                ${dishes.map(d => `
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <td style="padding: 12px 0; font-weight: 500;">${d.name}</td>
                        <td style="padding: 12px 0; text-align: right;">${d.orders}</td>
                        <td style="padding: 12px 0; text-align: right;">${d.quantity}</td>
                        <td style="padding: 12px 0; text-align: right; font-weight: 600;">${fmtINR(d.revenue)}</td>
                        <td style="padding: 12px 0; text-align: right;">
                            <span style="color: ${d.margin_pct > 30 ? 'var(--kiq-success-600)' : d.margin_pct > 15 ? 'var(--kiq-warning-600)' : 'var(--kiq-danger-600)'}; font-weight: 500;">
                                ${d.margin_pct}%
                            </span>
                        </td>
                        <td style="padding: 12px 0; text-align: right;">
                            <span class="kiq-badge kiq-badge-${CLASS_BADGE[d.classification]}">${d.classification}</span>
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
    const filtered = q ? allDishes.filter(d => d.name.toLowerCase().includes(q)) : allDishes;
    renderTable(filtered);
});

document.getElementById('periodSelect').addEventListener('change', loadDishes);

loadDishes();