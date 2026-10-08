/* KitchenIQ — Team JS */
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

const ROLE_META = {
    owner:   { label: 'Owner',   icon: '👑', color: '#f59e0b', canEdit: false },
    manager: { label: 'Manager', icon: '📊', color: '#3b82f6', canEdit: true },
    staff:   { label: 'Staff',   icon: '👨‍🍳', color: '#10b981', canEdit: true },
    analyst: { label: 'Analyst', icon: '📈', color: '#8b5cf6', canEdit: true },
};

const ROLE_DESC = {
    owner:   'You have full access to everything.',
    manager: 'You can manage orders, analytics, and team.',
    staff:   'You can view orders and food cost.',
    analyst: 'You have read-only access to analytics.',
    none:    'You do not have access to this kitchen.',
};

let myRole = null;

function toast(msg, type = 'success') {
    const colors = { success: '#10b981', danger: '#ef4444', info: '#3b82f6' };
    const el = document.createElement('div');
    el.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 99999;
        background: ${colors[type]}; color: white;
        padding: 12px 20px; border-radius: 8px;
        font-size: 14px; font-weight: 500;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        transition: all 0.3s ease;
        transform: translateX(100%); opacity: 0;
    `;
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(() => {
        el.style.transform = 'translateX(0)';
        el.style.opacity = '1';
    });
    setTimeout(() => {
        el.style.transform = 'translateX(100%)';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 300);
    }, 3000);
}

// ============================================================
// LOAD MY ROLE
// ============================================================
async function loadMyRole() {
    try {
        const res = await fetch(`${API}/api/team/me`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();
        myRole = d.role;

        document.getElementById('myRole').textContent = ROLE_META[myRole]?.label || myRole;
        document.getElementById('roleDesc').textContent = ROLE_DESC[myRole] || '';
        document.getElementById('userRole').textContent = ROLE_META[myRole]?.label || 'Member';

        // Show add button only for owner/manager
        if (myRole === 'owner' || myRole === 'manager') {
            document.getElementById('addMemberBtn').style.display = 'inline-flex';
        }
    } catch (e) {
        console.error(e);
    }
}

// ============================================================
// LOAD MEMBERS
// ============================================================
async function loadMembers() {
    try {
        const res = await fetch(`${API}/api/team/`, {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const members = await res.json();

        const grid = document.getElementById('teamGrid');

        if (!members.length) {
            grid.innerHTML = '<p style="text-align:center; padding: 40px; color: var(--kiq-text-muted);">No team members yet.</p>';
            return;
        }

        grid.style.display = 'grid';
        grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(260px, 1fr))';
        grid.style.gap = '16px';

        grid.innerHTML = members.map(m => {
            const meta = ROLE_META[m.role] || ROLE_META.staff;
            const initial = (m.full_name || m.email)[0].toUpperCase();
            const isMe = m.is_current_user;

            return `
                <div class="kiq-card kiq-card-hover" style="position: relative;">
                    ${isMe ? '<span class="kiq-badge kiq-badge-info" style="position: absolute; top: 12px; right: 12px; font-size: 10px;">YOU</span>' : ''}

                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                        <div style="width: 48px; height: 48px; border-radius: 999px; background: ${meta.color}20; color: ${meta.color}; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 20px;">
                            ${initial}
                        </div>
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-weight: 600; font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${m.full_name}</div>
                            <div style="font-size: 12px; color: var(--kiq-text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${m.email}</div>
                        </div>
                    </div>

                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 500; background: ${meta.color}15; color: ${meta.color};">
                            ${meta.icon} ${meta.label}
                        </span>

                        ${!isMe && myRole === 'owner' && m.role !== 'owner' ? `
                            <div style="display: flex; gap: 4px;">
                                <select class="role-change kiq-input" data-mid="${m.id}" style="height: 28px; padding: 0 6px; font-size: 12px; width: auto;">
                                    <option value="">Change...</option>
                                    <option value="manager">Manager</option>
                                    <option value="staff">Staff</option>
                                    <option value="analyst">Analyst</option>
                                </select>
                                <button class="kiq-btn kiq-btn-ghost kiq-btn-sm" onclick="removeMember(${m.id}, '${m.full_name.replace(/'/g, "\\'")}')" title="Remove" style="padding: 4px 8px; height: 28px;">
                                    <i class="fa-solid fa-trash" style="font-size: 11px;"></i>
                                </button>
                            </div>
                        ` : ''}
                    </div>
                </div>`;
        }).join('');

        // Role change handlers
        grid.querySelectorAll('.role-change').forEach(sel => {
            sel.addEventListener('change', async (e) => {
                const newRole = e.target.value;
                if (!newRole) return;
                await updateRole(sel.dataset.mid, newRole);
            });
        });

    } catch (e) {
        console.error(e);
    }
}

// ============================================================
// ACTIONS
// ============================================================
async function updateRole(mid, role) {
    try {
        const res = await fetch(`${API}/api/team/${mid}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ role }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);
        toast('Role updated');
        loadMembers();
    } catch (e) {
        toast(e.message, 'danger');
    }
}

window.removeMember = async function(mid, name) {
    if (!confirm(`Remove ${name} from team?`)) return;
    try {
        const res = await fetch(`${API}/api/team/${mid}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + token },
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);
        toast('Member removed');
        loadMembers();
    } catch (e) {
        toast(e.message, 'danger');
    }
};

// ============================================================
// MODAL
// ============================================================
document.getElementById('addMemberBtn').addEventListener('click', () => {
    document.getElementById('addModal').style.display = 'flex';
});

document.getElementById('closeModal').addEventListener('click', () => {
    document.getElementById('addModal').style.display = 'none';
});

document.getElementById('addModal').addEventListener('click', (e) => {
    if (e.target.id === 'addModal') {
        e.target.style.display = 'none';
    }
});

document.getElementById('addForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const btn = e.target.querySelector('button[type=submit]');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="kiq-spinner"></span> Adding...';

    try {
        const res = await fetch(`${API}/api/team/invite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({
                full_name: fd.get('full_name'),
                email: fd.get('email'),
                password: fd.get('password'),
                role: fd.get('role'),
            }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);

        toast('Team member added');
        e.target.reset();
        document.getElementById('addModal').style.display = 'none';
        loadMembers();
    } catch (err) {
        toast(err.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
    }
});

// ============================================================
// INIT
// ============================================================
async function init() {
    await loadMyRole();
    await loadMembers();
}

init();