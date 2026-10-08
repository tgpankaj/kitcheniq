/* ============================================================
   KitchenIQ — Notifications Bell (Global)
   Drop this into any page: <script src="../js/notifications-bell.js"></script>
   Requires: <div id="kiq-bell-container"></div> in topbar
   ============================================================ */

(function () {
    const API = window.API_URL;
    const token = localStorage.getItem('token');
    if (!token) return;

    let lastUnread = 0;
    let isOpen = false;

    // ---------- Inject CSS ----------
    const style = document.createElement('style');
    style.textContent = `
        .kiq-bell-btn { position: relative; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 8px; color: #64748b; cursor: pointer; transition: all 0.15s; }
        .kiq-bell-btn:hover { background: #f1f5f9; color: #0f172a; }
        .kiq-bell-badge { position: absolute; top: 6px; right: 6px; min-width: 16px; height: 16px; padding: 0 4px; font-size: 10px; font-weight: 700; color: white; background: #ef4444; border-radius: 999px; display: flex; align-items: center; justify-content: center; border: 2px solid white; }
        .kiq-bell-badge.hidden { display: none; }
        .kiq-bell-panel { position: absolute; top: 56px; right: 16px; width: 380px; max-height: 480px; background: white; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 10px 40px rgba(15, 23, 42, 0.12); z-index: 1000; display: none; flex-direction: column; }
        .kiq-bell-panel.open { display: flex; }
        .kiq-bell-header { padding: 14px 16px; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; }
        .kiq-bell-header h4 { font-size: 14px; font-weight: 600; }
        .kiq-bell-header button { font-size: 12px; color: #2563eb; font-weight: 500; background: none; border: none; cursor: pointer; }
        .kiq-bell-list { overflow-y: auto; flex: 1; }
        .kiq-bell-item { padding: 12px 16px; border-bottom: 1px solid #f8fafc; cursor: pointer; display: flex; gap: 10px; transition: background 0.15s; }
        .kiq-bell-item:hover { background: #f8fafc; }
        .kiq-bell-item.unread { background: #f0f9ff; }
        .kiq-bell-dot { width: 8px; height: 8px; border-radius: 999px; flex-shrink: 0; margin-top: 6px; }
        .dot-info { background: #0ea5e9; } .dot-success { background: #10b981; }
        .dot-warning { background: #f59e0b; } .dot-danger { background: #ef4444; }
        .kiq-bell-title { font-size: 13px; font-weight: 600; color: #0f172a; }
        .kiq-bell-msg { font-size: 12px; color: #64748b; margin-top: 2px; }
        .kiq-bell-time { font-size: 10px; color: #94a3b8; margin-top: 4px; }
        .kiq-bell-empty { padding: 40px 20px; text-align: center; color: #94a3b8; font-size: 13px; }
        .kiq-bell-footer { padding: 10px; text-align: center; border-top: 1px solid #f1f5f9; }
        .kiq-bell-footer a { font-size: 12px; font-weight: 600; color: #2563eb; text-decoration: none; }
    `;
    document.head.appendChild(style);

    // ---------- Find insertion point ----------
    function findInsertPoint() {
        const container = document.getElementById('kiq-bell-container');
        if (container) return container;

        // Fallback: find topbar actions
        const actions = document.querySelector('.kiq-topbar-actions');
        if (actions) {
            const wrap = document.createElement('div');
            wrap.id = 'kiq-bell-container';
            actions.insertBefore(wrap, actions.firstChild);
            return wrap;
        }
        return null;
    }

    // ---------- Render Bell ----------
    function injectBell() {
        const container = findInsertPoint();
        if (!container) {
            setTimeout(injectBell, 200);
            return;
        }

        container.innerHTML = `
            <div class="kiq-bell-btn" id="kiq-bell-btn">
                <i class="fa-regular fa-bell" style="font-size: 18px;"></i>
                <span class="kiq-bell-badge hidden" id="kiq-bell-badge">0</span>
            </div>
            <div class="kiq-bell-panel" id="kiq-bell-panel">
                <div class="kiq-bell-header">
                    <h4>Notifications</h4>
                    <button id="kiq-mark-all">Mark all read</button>
                </div>
                <div class="kiq-bell-list" id="kiq-bell-list">
                    <div class="kiq-bell-empty">Loading...</div>
                </div>
                <div class="kiq-bell-footer">
                    <a href="notifications.html">View all notifications</a>
                </div>
            </div>
        `;

        document.getElementById('kiq-bell-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            isOpen = !isOpen;
            document.getElementById('kiq-bell-panel').classList.toggle('open', isOpen);
            if (isOpen) refresh();
        });

        document.getElementById('kiq-mark-all').addEventListener('click', async () => {
            await fetch(API + '/api/notifications/read-all', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
            });
            refresh();
        });

        document.addEventListener('click', (e) => {
            if (e.target.closest('#kiq-bell-panel') || e.target.closest('#kiq-bell-btn')) return;
            isOpen = false;
            document.getElementById('kiq-bell-panel').classList.remove('open');
        });
    }

    // ---------- Time ago ----------
    function timeAgo(iso) {
        if (!iso) return '';
        const then = new Date(iso.replace(' ', 'T') + 'Z');
        const s = Math.floor((Date.now() - then) / 1000);
        if (s < 60) return 'just now';
        if (s < 3600) return Math.floor(s / 60) + 'm ago';
        if (s < 86400) return Math.floor(s / 3600) + 'h ago';
        return Math.floor(s / 86400) + 'd ago';
    }

    // ---------- Refresh ----------
    async function refresh() {
        try {
            const [listRes, countRes] = await Promise.all([
                fetch(API + '/api/notifications/?limit=10', { headers: { 'Authorization': 'Bearer ' + token } }),
                fetch(API + '/api/notifications/unread-count', { headers: { 'Authorization': 'Bearer ' + token } }),
            ]);

            const items = await listRes.json();
            const count = (await countRes.json()).unread || 0;

            // Badge
            const badge = document.getElementById('kiq-bell-badge');
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }

            // Alert on new
            if (lastUnread > 0 && count > lastUnread && items.length) {
                if (window.showToast) {
                    window.showToast(items[0].title, items[0].severity);
                }
            }
            lastUnread = count;

            // List
            const list = document.getElementById('kiq-bell-list');
            if (!items.length) {
                list.innerHTML = '<div class="kiq-bell-empty"><i class="fa-regular fa-bell-slash" style="font-size: 24px; margin-bottom: 8px;"></i><br>No notifications yet</div>';
                return;
            }

            list.innerHTML = items.map(n => `
                <div class="kiq-bell-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}" data-link="${n.link || ''}">
                    <span class="kiq-bell-dot dot-${n.severity}"></span>
                    <div style="flex: 1; min-width: 0;">
                        <div class="kiq-bell-title">${n.title}</div>
                        ${n.message ? `<div class="kiq-bell-msg">${n.message}</div>` : ''}
                        <div class="kiq-bell-time">${timeAgo(n.created_at)}</div>
                    </div>
                </div>
            `).join('');

            list.querySelectorAll('.kiq-bell-item').forEach(el => {
                el.addEventListener('click', async () => {
                    const id = el.dataset.id;
                    const link = el.dataset.link;
                    await fetch(API + `/api/notifications/${id}/read`, {
                        method: 'POST',
                        headers: { 'Authorization': 'Bearer ' + token },
                    });
                    if (link && link !== 'null') window.location.href = link;
                    else refresh();
                });
            });

        } catch (e) {
            console.warn('[bell] refresh failed:', e);
        }
    }

    // ---------- Polling ----------
    injectBell();
    setTimeout(refresh, 500);
    setInterval(refresh, 20000);
})();