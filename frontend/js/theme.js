/* ============================================================
   KitchenIQ — Theme Toggle (Global)
   Adds a theme switcher button in topbar.
   Supports: light | dark | system
   ============================================================ */

(function () {
    const STORAGE_KEY = 'kiq-theme';
    const THEMES = ['light', 'dark', 'system'];

    // ---------- Apply theme ----------
    function applyTheme(theme) {
        const root = document.documentElement;

        if (theme === 'system') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        } else {
            root.setAttribute('data-theme', theme);
        }

        // Notify charts to re-render (custom event)
        window.dispatchEvent(new CustomEvent('kiq:theme-changed', { detail: { theme } }));
    }

    // ---------- Get current ----------
    function getTheme() {
        return localStorage.getItem(STORAGE_KEY) || 'system';
    }

    // ---------- Icon for theme ----------
    function iconFor(theme) {
        if (theme === 'dark') return 'fa-moon';
        if (theme === 'light') return 'fa-sun';
        return 'fa-circle-half-stroke';
    }

    // ---------- Inject CSS ----------
    const style = document.createElement('style');
    style.textContent = `
        .kiq-theme-btn {
            position: relative;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            color: var(--kiq-text-muted);
            cursor: pointer;
            transition: all 0.15s;
        }
        .kiq-theme-btn:hover {
            background: var(--kiq-bg-hover);
            color: var(--kiq-text);
        }
        .kiq-theme-menu {
            position: absolute;
            top: 52px;
            right: 0;
            background: var(--kiq-bg-elevated);
            border: 1px solid var(--kiq-border);
            border-radius: 10px;
            box-shadow: var(--kiq-shadow-lg);
            padding: 6px;
            min-width: 160px;
            z-index: 1000;
            display: none;
        }
        .kiq-theme-menu.open { display: block; }
        .kiq-theme-option {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            color: var(--kiq-text);
            transition: background 0.1s;
        }
        .kiq-theme-option:hover {
            background: var(--kiq-bg-hover);
        }
        .kiq-theme-option.active {
            background: var(--kiq-brand-50);
            color: var(--kiq-brand-600);
            font-weight: 500;
        }
        .kiq-theme-option i {
            width: 16px;
            text-align: center;
            font-size: 13px;
        }
        .kiq-theme-option .check {
            margin-left: auto;
            color: var(--kiq-brand-600);
            display: none;
        }
        .kiq-theme-option.active .check { display: inline; }
        .kiq-theme-wrap { position: relative; }
    `;
    document.head.appendChild(style);

    // ---------- Inject toggle button ----------
    function injectButton() {
        const actions = document.querySelector('.kiq-topbar-actions');
        if (!actions) {
            setTimeout(injectButton, 200);
            return;
        }

        if (document.getElementById('kiq-theme-btn')) return;

        const wrap = document.createElement('div');
        wrap.className = 'kiq-theme-wrap';
        wrap.innerHTML = `
            <div class="kiq-theme-btn" id="kiq-theme-btn" title="Change theme">
                <i class="fa-solid ${iconFor(getTheme())}" style="font-size: 16px;"></i>
            </div>
            <div class="kiq-theme-menu" id="kiq-theme-menu">
                <div class="kiq-theme-option" data-theme="light">
                    <i class="fa-solid fa-sun"></i>
                    <span>Light</span>
                    <i class="fa-solid fa-check check"></i>
                </div>
                <div class="kiq-theme-option" data-theme="dark">
                    <i class="fa-solid fa-moon"></i>
                    <span>Dark</span>
                    <i class="fa-solid fa-check check"></i>
                </div>
                <div class="kiq-theme-option" data-theme="system">
                    <i class="fa-solid fa-circle-half-stroke"></i>
                    <span>System</span>
                    <i class="fa-solid fa-check check"></i>
                </div>
            </div>
        `;

        // Insert before notification bell
        const bell = document.getElementById('kiq-bell-container');
        if (bell) {
            actions.insertBefore(wrap, bell);
        } else {
            actions.insertBefore(wrap, actions.firstChild);
        }

        updateMenuState();

        // Handlers
        document.getElementById('kiq-theme-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('kiq-theme-menu').classList.toggle('open');
        });

        document.querySelectorAll('.kiq-theme-option').forEach(opt => {
            opt.addEventListener('click', () => {
                const theme = opt.dataset.theme;
                localStorage.setItem(STORAGE_KEY, theme);
                applyTheme(theme);
                updateMenuState();
                document.getElementById('kiq-theme-menu').classList.remove('open');
            });
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.kiq-theme-wrap')) {
                document.getElementById('kiq-theme-menu')?.classList.remove('open');
            }
        });
    }

    function updateMenuState() {
        const current = getTheme();
        document.querySelectorAll('.kiq-theme-option').forEach(opt => {
            opt.classList.toggle('active', opt.dataset.theme === current);
        });

        const btnIcon = document.querySelector('#kiq-theme-btn i');
        if (btnIcon) {
            btnIcon.className = 'fa-solid ' + iconFor(current);
        }
    }

    // ---------- Listen to system changes ----------
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (getTheme() === 'system') applyTheme('system');
    });

    // ---------- Apply on load (before paint to avoid flash) ----------
    applyTheme(getTheme());

    // ---------- Inject after DOM ready ----------
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectButton);
    } else {
        injectButton();
    }
})();