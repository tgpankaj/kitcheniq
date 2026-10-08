/* ============================================================
   KitchenIQ — Global Search
   Replaces topbar search input with functional search
   + Cmd/Ctrl+K shortcut + dropdown results
   ============================================================ */

(function () {
    const API = window.API_URL;
    const token = localStorage.getItem('token');
    if (!token) return;

    let searchInput = null;
    let panel = null;
    let timer = null;
    let currentFocus = -1;
    let results = [];

    // ---------- Inject CSS ----------
    const style = document.createElement('style');
    style.textContent = `
        #kiq-search-panel {
            position: absolute;
            top: 52px;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(15, 23, 42, 0.12);
            z-index: 1000;
            max-height: 400px;
            overflow-y: auto;
            display: none;
        }
        #kiq-search-panel.open { display: block; }
        .kiq-search-result {
            padding: 10px 14px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            border-bottom: 1px solid #f8fafc;
            transition: background 0.1s;
        }
        .kiq-search-result:last-child { border-bottom: none; }
        .kiq-search-result:hover, .kiq-search-result.active {
            background: #f0f9ff;
        }
        .kiq-search-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: #dbeafe;
            color: #2563eb;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .kiq-search-label { font-size: 13px; font-weight: 600; color: #0f172a; }
        .kiq-search-sub { font-size: 11px; color: #64748b; margin-top: 1px; }
        .kiq-search-empty {
            padding: 30px 20px;
            text-align: center;
            color: #94a3b8;
            font-size: 13px;
        }
        .kiq-search-header {
            padding: 6px 14px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            background: #fafbfc;
            border-bottom: 1px solid #f1f5f9;
        }
        #kiq-search-wrap { position: relative; }
    `;
    document.head.appendChild(style);

    // ---------- Find Topbar Search ----------
    function findSearch() {
        const input = document.querySelector('.kiq-topbar-search input');
        if (!input) {
            setTimeout(findSearch, 200);
            return;
        }

        searchInput = input;
        searchInput.removeAttribute('disabled');
        searchInput.placeholder = 'Search orders, dishes, customers... (⌘K)';

        // Wrap in relative container
        const wrap = searchInput.closest('.kiq-topbar-search');
        if (wrap) {
            wrap.id = 'kiq-search-wrap';
            wrap.style.position = 'relative';
        }

        // Create panel
        panel = document.createElement('div');
        panel.id = 'kiq-search-panel';
        document.body.appendChild(panel);

        // Position panel under input
        const updatePosition = () => {
            if (!wrap || !panel) return;
            const rect = wrap.getBoundingClientRect();
            panel.style.position = 'fixed';
            panel.style.top = (rect.bottom + 6) + 'px';
            panel.style.left = rect.left + 'px';
            panel.style.width = rect.width + 'px';
        };

        window.addEventListener('resize', updatePosition);
        window.addEventListener('scroll', updatePosition, true);
        updatePosition();

        // Events
        searchInput.addEventListener('input', onInput);
        searchInput.addEventListener('keydown', onKey);
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.length >= 2) doSearch(searchInput.value);
        });

        document.addEventListener('click', (e) => {
            if (e.target.closest('#kiq-search-panel') || e.target.closest('#kiq-search-wrap')) return;
            closePanel();
        });

        // Cmd/Ctrl+K to focus
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
            if (e.key === 'Escape') closePanel();
        });
    }

    // ---------- Input handler ----------
    function onInput(e) {
        const q = e.target.value.trim();
        clearTimeout(timer);
        if (q.length < 2) { closePanel(); return; }
        timer = setTimeout(() => doSearch(q), 200);
    }

    // ---------- Keyboard nav ----------
    function onKey(e) {
        const items = panel.querySelectorAll('.kiq-search-result');
        if (!panel.classList.contains('open') || !items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentFocus = (currentFocus + 1) % items.length;
            updateActive(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentFocus = (currentFocus - 1 + items.length) % items.length;
            updateActive(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (currentFocus >= 0 && items[currentFocus]) {
                items[currentFocus].click();
            }
        }
    }

    function updateActive(items) {
        items.forEach((el, i) => {
            el.classList.toggle('active', i === currentFocus);
            if (i === currentFocus) el.scrollIntoView({ block: 'nearest' });
        });
    }

    // ---------- Search ----------
    async function doSearch(q) {
        try {
            const res = await fetch(API + '/api/search/quick?q=' + encodeURIComponent(q), {
                headers: { 'Authorization': 'Bearer ' + token },
            });
            const data = await res.json();
            renderResults(data);
        } catch (e) {
            console.warn('[search] failed:', e);
        }
    }

    function renderResults(items) {
        if (!items.length) {
            panel.innerHTML = '<div class="kiq-search-empty">No results found.</div>';
            panel.classList.add('open');
            return;
        }

        panel.innerHTML = items.map((r, i) => `
            <div class="kiq-search-result" data-link="${r.link}" data-idx="${i}">
                <div class="kiq-search-icon"><i class="fa-solid ${r.icon}"></i></div>
                <div style="flex: 1; min-width: 0;">
                    <div class="kiq-search-label">${escapeHtml(r.label)}</div>
                    <div class="kiq-search-sub">${escapeHtml(r.sub || r.type)}</div>
                </div>
                <i class="fa-solid fa-arrow-right" style="color: #cbd5e1; font-size: 12px;"></i>
            </div>
        `).join('');

        panel.classList.add('open');
        currentFocus = -1;

        panel.querySelectorAll('.kiq-search-result').forEach(el => {
            el.addEventListener('click', () => {
                window.location.href = el.dataset.link;
            });
        });
    }

    function closePanel() {
        if (panel) panel.classList.remove('open');
        currentFocus = -1;
    }

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    // ---------- Boot ----------
    findSearch();
})();