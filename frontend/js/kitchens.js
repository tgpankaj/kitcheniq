/* KitchenIQ — Kitchens Page JS */
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

function toast(msg, type = 'success') {
    const colors = { success: '#10b981', danger: '#ef4444', info: '#3b82f6' };
    const el = document.createElement('div');
    el.style.cssText = `position: fixed; top: 20px; right: 20px; z-index: 99999; background: ${colors[type]}; color: white; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; box-shadow: 0 10px 40px rgba(0,0,0,0.15); transition: all 0.3s; transform: translateX(100%); opacity: 0;`;
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(() => { el.style.transform = 'translateX(0)'; el.style.opacity = '1'; });
    setTimeout(() => { el.style.transform = 'translateX(100%)'; el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3000);
}

function fmtINR(n) { return '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }

let currentKitchenId = null;

async function loadKitchens() {
    try {
        const res = await fetch(API + '/api/kitchens/', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const kitchens = await res.json();

        const current = JSON.parse(localStorage.getItem('kitchen') || '{}');
        currentKitchenId = current.id;

        const grid = document.getElementById('kitchensGrid');

        if (!kitchens.length) {
            grid.innerHTML = '<p style="grid-column: 1 / -1; text-align:center; padding: 40px; color: var(--kiq-text-muted);">No kitchens yet.</p>';
            return;
        }

        grid.innerHTML = kitchens.map(k => `
            <div class="kiq-card kiq-card-hover" style="position: relative;">
                ${k.id === currentKitchenId ? '<span class="kiq-badge kiq-badge-success" style="position: absolute; top: 12px; right: 12px;">ACTIVE</span>' : ''}
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: var(--kiq-brand-100); color: var(--kiq-brand-600); display: flex; align-items: center; justify-content: center; font-size: 20px;">
                        <i class="fa-solid fa-store"></i>
                    </div>
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-weight: 600; font-size: 15px;">${k.name}</div>
                        <div style="font-size: 12px; color: var(--kiq-text-muted);">${k.city || 'No city'}</div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 12px; background: var(--kiq-bg-sunken); border-radius: 8px; margin-bottom: 14px;">
                    <div>
                        <div style="font-size: 10px; color: var(--kiq-text-muted); text-transform: uppercase;">Orders</div>
                        <div style="font-weight: 600; font-size: 16px;">${k.total_orders}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--kiq-text-muted); text-transform: uppercase;">Revenue</div>
                        <div style="font-weight: 600; font-size: 16px;">${fmtINR(k.total_revenue)}</div>
                    </div>
                </div>

                <div style="display: flex; gap: 8px;">
                    ${k.id !== currentKitchenId ? `
                        <button class="kiq-btn kiq-btn-primary kiq-btn-sm" onclick="switchTo(${k.id}, '${k.name.replace(/'/g, "\\'")}')" style="flex: 1;">
                            <i class="fa-solid fa-arrow-right-arrow-left"></i> Switch
                        </button>
                    ` : ''}
                    <button class="kiq-btn kiq-btn-secondary kiq-btn-sm" onclick="editKitchen(${k.id})">
                        <i class="fa-solid fa-pen"></i>
                    </button>
                    ${kitchens.length > 1 ? `
                        <button class="kiq-btn kiq-btn-ghost kiq-btn-sm" onclick="deleteKitchen(${k.id}, '${k.name.replace(/'/g, "\\'")}')" style="color: var(--kiq-danger-600);">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

    } catch (e) { console.error(e); }
}

window.switchTo = function(id, name) {
    localStorage.setItem('kitchen', JSON.stringify({ id, name }));
    toast(`Switched to ${name}`);
    setTimeout(() => window.location.href = 'dashboard.html', 600);
};

window.editKitchen = async function(id) {
    try {
        const res = await fetch(`${API}/api/kitchens/${id}`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const k = await res.json();

        document.getElementById('modalTitle').textContent = 'Edit Kitchen';
        document.getElementById('kitchenId').value = k.id;
        document.querySelector('[name=name]').value = k.name || '';
        document.querySelector('[name=city]').value = k.city || '';
        document.querySelector('[name=address]').value = k.address || '';
        document.querySelector('[name=phone]').value = k.phone || '';

        document.getElementById('kitchenModal').style.display = 'flex';
    } catch (e) { toast(e.message, 'danger'); }
};

window.deleteKitchen = async function(id, name) {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;

    try {
        const res = await fetch(`${API}/api/kitchens/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);
        toast('Kitchen deleted');
        loadKitchens();
    } catch (e) { toast(e.message, 'danger'); }
};

// Modal
document.getElementById('addKitchenBtn').addEventListener('click', () => {
    document.getElementById('modalTitle').textContent = 'Add New Kitchen';
    document.getElementById('kitchenForm').reset();
    document.getElementById('kitchenId').value = '';
    document.getElementById('kitchenModal').style.display = 'flex';
});

document.getElementById('closeModal').addEventListener('click', () => {
    document.getElementById('kitchenModal').style.display = 'none';
});

document.getElementById('kitchenModal').addEventListener('click', (e) => {
    if (e.target.id === 'kitchenModal') e.target.style.display = 'none';
});

document.getElementById('kitchenForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const id = fd.get('id');
    const body = {
        name: fd.get('name'),
        city: fd.get('city'),
        address: fd.get('address'),
        phone: fd.get('phone'),
    };

    const btn = e.target.querySelector('button[type=submit]');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="kiq-spinner"></span> Saving...';

    try {
        const url = id ? `${API}/api/kitchens/${id}` : `${API}/api/kitchens/`;
        const method = id ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(body),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);
        toast(id ? 'Kitchen updated' : 'Kitchen created');
        document.getElementById('kitchenModal').style.display = 'none';
        loadKitchens();
    } catch (err) {
        toast(err.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
    }
});

loadKitchens();