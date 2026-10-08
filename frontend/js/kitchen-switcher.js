/* ============================================================
   KitchenIQ — Kitchen Switcher
   Dropdown in topbar to switch between kitchens/branches.
   ============================================================ */

(function () {
    const API = window.API_URL;
    const token = localStorage.getItem('token');
    if (!token) return;

    let kitchens = [];
    let currentKitchenId = null;

    // ---------- CSS ----------
    const style = document.createElement('style');
    style.textContent = `
        .kiq-kitchen-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 8px;
            background: var(--kiq-bg-sunken);
            border: 1px solid var(--kiq-border);
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            color: var(--kiq-text);
            transition: all 0.15s;
            max-width: 240px;
        }
        .kiq-kitchen-btn:hover {
            background: var(--kiq-bg-hover);
            border-color: var(--kiq-border-strong);
        }
        .kiq-kitchen-btn .name {
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .kiq-kitchen-menu {
            position: absolute;
            top: 52px;
            right: 0;
            background: var(--kiq-bg-elevated);
            border: 1px solid var(--kiq-border);
            border-radius: 10px;
            box-shadow: var(--kiq-shadow-lg);
            padding: 6px;
            min-width: 260px;
            max-width: 320px;
            z-index: 1000;
            display: none;
        }
        .kiq-kitchen-menu.open { display: block; }
        .kiq-kitchen-menu-label {
            padding: 6px 12px 4px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--kiq-text-subtle);
        }
        .kiq-kitchen-option {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            color: var(--kiq-text);
            transition: background 0.1s;
        }
        .kiq-kitchen-option:hover {
            background: var(--kiq-bg-hover);
        }
        .kiq-kitchen-option.active {
            background: var(--kiq-brand-50);
            color: var(--kiq-brand-600);
        }
        .kiq-kitchen-option .check {
            margin-left: auto;
            color: var(--kiq-brand-600);
            display: none;
        }
        .kiq-kitchen-option.active .check { display: inline; }
        .kiq-kitchen-option .info {
            flex: 1;
            min-width: 0;
        }
        .kiq-kitchen-option .sub {
            font-size: 11px;
            color: var(--kiq-text-muted);
            margin-top: 1px;
        }
        .kiq-kitchen-add {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-top: 1px solid var(--kiq-border);
            margin-top: 6px;
            padding-top: 12px;
            cursor: pointer;
            font-size: 13px;
            color: var(--kiq-brand-600);
            font-weight: 500;
        }
        .kiq-kitchen-add:hover { background: var(--kiq-brand-50); border-radius: 6px; }
    `;
    document.head.appendChild(style);

    // ---------- Find insertion ----------
    function findTopbar() {
        const actions = document.querySelector('.kiq-topbar-actions');
        if (!actions) {
            setTimeout(findTopbar, 200);
            return;
        }
        if (document.getElementById('kiq-kitchen-wrap')) return;

        const wrap = document.createElement('div');
        wrap.id = 'kiq-kitchen-wrap';
        wrap.style.cssText = 'position: relative;';
        wrap.innerHTML = `
            <div class="kiq-kitchen-btn" id="kiq-kitchen-btn">
                <i class="fa-solid fa-store" style="color: var(--kiq-brand-600);"></i>
                <span class="name" id="kiq-kitchen-name">Loading...</span>
                <i class="fa-solid fa-chevron-down" style="font-size: 10px; color: var(--kiq-text-subtle);"></i>
            </div>
            <div class="kiq-kitchen-menu" id="kiq-kitchen-menu">
                <div class="kiq-kitchen-menu-label">Your Kitchens</div>
                <div id="kiq-kitchen-list"></div>
                <div class="kiq-kitchen-add" id="kiq-kitchen-add">
                    <i class="fa-solid fa-plus"></i>
                    <span>Add New Kitchen</span>
                </div>
            </div>
        `;

        // Insert as first child of actions
        actions.insertBefore(wrap, actions.firstChild);

        // Handlers
        document.getElementById('kiq-kitchen-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('kiq-kitchen-menu').classList.toggle('open');
        });

        document.getElementById('kiq-kitchen-add').addEventListener('click', () => {
            window.location.href = '/pages/kitchens.html';
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('#kiq-kitchen-wrap')) {
                document.getElementById('kiq-kitchen-menu')?.classList.remove('open');
            }
        });

        loadKitchens();
    }

    // ---------- Load ----------
    async function loadKitchens() {
        try {
            const res = await fetch(API + '/api/kitchens/', {
                headers: { 'Authorization': 'Bearer ' + token },
            });
            kitchens = await res.json();

            // Get current from localStorage or first
            const stored = JSON.parse(localStorage.getItem('kitchen') || '{}');
            currentKitchenId = stored.id || (kitchens[0]?.id);

            // Sync localStorage with server data
            const current = kitchens.find(k => k.id === currentKitchenId) || kitchens[0];
            if (current) {
                currentKitchenId = current.id;
                localStorage.setItem('kitchen', JSON.stringify({
                    id: current.id,
                    name: current.name,
                }));
                document.getElementById('kiq-kitchen-name').textContent = current.name;
            }

            renderMenu();
        } catch (e) {
            console.error('[kitchen] load failed:', e);
        }
    }

    function renderMenu() {
        const list = document.getElementById('kiq-kitchen-list');
        if (!list) return;

        list.innerHTML = kitchens.map(k => `
            <div class="kiq-kitchen-option ${k.id === currentKitchenId ? 'active' : ''}" data-id="${k.id}" data-name="${k.name}">
                <i class="fa-solid fa-store" style="color: var(--kiq-text-muted); font-size: 13px;"></i>
                <div class="info">
                    <div>${escapeHtml(k.name)}</div>
                    <div class="sub">${k.total_orders} orders · ₹${Number(k.total_revenue).toLocaleString('en-IN')}</div>
                </div>
                <i class="fa-solid fa-check check"></i>
            </div>
        `).join('');

        list.querySelectorAll('.kiq-kitchen-option').forEach(el => {
            el.addEventListener('click', () => {
                const id = parseInt(el.dataset.id);
                const name = el.dataset.name;
                switchKitchen(id, name);
            });
        });
    }

    function switchKitchen(id, name) {
        localStorage.setItem('kitchen', JSON.stringify({ id, name }));
        currentKitchenId = id;

        // Visual update
        document.getElementById('kiq-kitchen-name').textContent = name;
        document.getElementById('kiq-kitchen-menu').classList.remove('open');

        // Show toast
        if (window.showToast) window.showToast(`Switched to ${name}`, 'success');

        // Reload page (all data will re-fetch with new kitchen)
        setTimeout(() => window.location.reload(), 400);
    }

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    // Boot
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', findTopbar);
    } else {
        findTopbar();
    }
})();