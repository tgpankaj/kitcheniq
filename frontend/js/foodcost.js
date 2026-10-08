/* KitchenIQ — Food Cost JS */
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
function fmtINR2(n) {
    return '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

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
// SUMMARY
// ============================================================
async function loadSummary() {
    try {
        const res = await fetch(`${API}/api/foodcost/summary`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();
        document.getElementById('kpiIngredients').textContent = d.total_ingredients;
        document.getElementById('kpiStockValue').textContent = fmtINR(d.stock_value);
        document.getElementById('kpiLowStock').textContent = d.low_stock_count;
        document.getElementById('kpiCoverage').textContent = d.recipe_coverage_pct + '%';
    } catch (e) { console.error(e); }
}

// ============================================================
// DISH COSTING
// ============================================================
async function loadCosting() {
    const days = document.getElementById('periodSelect').value;
    try {
        const res = await fetch(`${API}/api/foodcost/dish-costing?days=${days}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        if (!data.length) {
            document.getElementById('costingTable').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No dishes yet. Upload CSV first.</p>';
            return;
        }

        document.getElementById('costingTable').innerHTML = `
            <table style="width: 100%; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Dish</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Qty</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Avg Price</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Food Cost/Unit</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Total Cost</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Profit</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Margin</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(d => `
                        <tr style="border-bottom: 1px solid var(--kiq-border);">
                            <td style="padding: 12px 0; font-weight: 500;">
                                ${d.name}
                                ${!d.has_recipe ? '<span class="kiq-badge kiq-badge-warning" style="margin-left: 6px; font-size: 10px;">No recipe</span>' : ''}
                            </td>
                            <td style="padding: 12px 0; text-align: right;">${d.quantity}</td>
                            <td style="padding: 12px 0; text-align: right;">${fmtINR2(d.avg_price)}</td>
                            <td style="padding: 12px 0; text-align: right;">${d.cost_per_unit !== null ? fmtINR2(d.cost_per_unit) : '—'}</td>
                            <td style="padding: 12px 0; text-align: right;">${fmtINR2(d.food_cost)}</td>
                            <td style="padding: 12px 0; text-align: right; font-weight: 600; color: ${d.profit >= 0 ? 'var(--kiq-success-600)' : 'var(--kiq-danger-600)'};">${fmtINR2(d.profit)}</td>
                            <td style="padding: 12px 0; text-align: right;">
                                <span class="kiq-badge kiq-badge-${d.margin_pct > 40 ? 'success' : d.margin_pct > 20 ? 'warning' : 'danger'}">${d.margin_pct}%</span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    } catch (e) { console.error(e); }
}

// ============================================================
// INGREDIENTS
// ============================================================
async function loadIngredients() {
    try {
        const res = await fetch(`${API}/api/foodcost/ingredients`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        // Populate recipe dropdown
        const sel = document.getElementById('recipeIngredientSelect');
        sel.innerHTML = '<option value="">Select ingredient...</option>' +
            data.map(i => `<option value="${i.id}">${i.name} (${i.unit})</option>`).join('');

        if (!data.length) {
            document.getElementById('ingredientsTable').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No ingredients yet. Add one above.</p>';
            return;
        }

        document.getElementById('ingredientsTable').innerHTML = `
            <table style="width: 100%; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--kiq-border);">
                        <th style="text-align: left; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Name</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Unit</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Cost/Unit</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Stock</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Total Value</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;">Status</th>
                        <th style="text-align: right; padding: 10px 0; font-size: 11px; text-transform: uppercase; color: var(--kiq-text-muted); font-weight: 500;"></th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(i => `
                        <tr style="border-bottom: 1px solid var(--kiq-border);">
                            <td style="padding: 12px 0; font-weight: 500;">${i.name}</td>
                            <td style="padding: 12px 0; text-align: right; color: var(--kiq-text-muted);">${i.unit}</td>
                            <td style="padding: 12px 0; text-align: right;">${fmtINR2(i.cost_per_unit)}</td>
                            <td style="padding: 12px 0; text-align: right;">${i.current_stock}</td>
                            <td style="padding: 12px 0; text-align: right; font-weight: 600;">${fmtINR2(i.cost_per_unit * i.current_stock)}</td>
                            <td style="padding: 12px 0; text-align: right;">
                                ${i.low_stock
                                    ? '<span class="kiq-badge kiq-badge-danger">Low stock</span>'
                                    : '<span class="kiq-badge kiq-badge-success">OK</span>'}
                            </td>
                            <td style="padding: 12px 0; text-align: right;">
                                <button class="kiq-btn kiq-btn-ghost kiq-btn-sm" onclick="deleteIngredient(${i.id})" title="Delete">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    } catch (e) { console.error(e); }
}

// Add ingredient form
document.getElementById('ingredientForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = {
        name: fd.get('name'),
        unit: fd.get('unit'),
        cost_per_unit: parseFloat(fd.get('cost_per_unit')) || 0,
        current_stock: parseFloat(fd.get('current_stock')) || 0,
        reorder_threshold: parseFloat(fd.get('reorder_threshold')) || 0,
    };

    try {
        const res = await fetch(`${API}/api/foodcost/ingredients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(body),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);
        e.target.reset();
        loadIngredients();
        loadSummary();
    } catch (err) {
        alert('Error: ' + err.message);
    }
});

window.deleteIngredient = async function(id) {
    if (!confirm('Delete this ingredient?')) return;
    await fetch(`${API}/api/foodcost/ingredients/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + token },
    });
    loadIngredients();
    loadSummary();
};

// ============================================================
// RECIPES
// ============================================================
async function loadRecipes() {
    try {
        const res = await fetch(`${API}/api/foodcost/recipes`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const data = await res.json();

        if (!data.length) {
            document.getElementById('recipesTable').innerHTML =
                '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No recipes yet. Add ingredients first, then map them to dishes.</p>';
            return;
        }

        // Group by dish
        const grouped = {};
        data.forEach(r => {
            if (!grouped[r.dish]) grouped[r.dish] = [];
            grouped[r.dish].push(r);
        });

        document.getElementById('recipesTable').innerHTML = Object.entries(grouped).map(([dish, items]) => {
            const totalCost = items.reduce((s, i) => s + i.line_cost, 0);
            return `
                <div style="padding: 16px 0; border-bottom: 1px solid var(--kiq-border);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong style="font-size: 15px;">${dish}</strong>
                        <span class="kiq-badge kiq-badge-brand">Cost: ${fmtINR2(totalCost)}</span>
                    </div>
                    <div style="font-size: 13px; color: var(--kiq-text-muted);">
                        ${items.map(i => `
                            <span style="display: inline-flex; align-items: center; margin-right: 12px;">
                                ${i.ingredient_name}: <strong style="margin-left: 4px;">${i.quantity} ${i.unit}</strong>
                                <button class="kiq-btn kiq-btn-ghost kiq-btn-sm" onclick="deleteRecipe(${i.id})" style="padding: 2px 6px; height: 22px;">
                                    <i class="fa-solid fa-xmark" style="font-size: 11px;"></i>
                                </button>
                            </span>
                        `).join('')}
                    </div>
                </div>`;
        }).join('');
    } catch (e) { console.error(e); }
}

document.getElementById('recipeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = {
        dish: fd.get('dish'),
        ingredient_id: parseInt(fd.get('ingredient_id')),
        quantity: parseFloat(fd.get('quantity')),
    };

    try {
        const res = await fetch(`${API}/api/foodcost/recipes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(body),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);
        e.target.reset();
        loadRecipes();
        loadCosting();
        loadSummary();
    } catch (err) {
        alert('Error: ' + err.message);
    }
});

window.deleteRecipe = async function(id) {
    await fetch(`${API}/api/foodcost/recipes/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + token },
    });
    loadRecipes();
    loadCosting();
    loadSummary();
};

// ============================================================
// INIT
// ============================================================
function loadAll() {
    loadSummary();
    loadCosting();
    loadIngredients();
    loadRecipes();
}

document.getElementById('periodSelect').addEventListener('change', loadCosting);

loadAll();