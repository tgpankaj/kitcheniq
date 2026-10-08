-- ============================================================
-- KitchenIQ — Migration 005: Performance Indexes
-- ============================================================

BEGIN;

-- Orders indexes (already exists most)
CREATE INDEX IF NOT EXISTS idx_orders_kitchen_date_status
    ON orders(kitchen_id, order_date DESC, status);

CREATE INDEX IF NOT EXISTS idx_orders_kitchen_platform_date
    ON orders(kitchen_id, platform, order_date DESC);

-- Order items
CREATE INDEX IF NOT EXISTS idx_order_items_name_kitchen
    ON order_items(item_name);

-- Notifications
CREATE INDEX IF NOT EXISTS idx_notifications_user_created
    ON notifications(user_id, created_at DESC);

-- Sync logs
CREATE INDEX IF NOT EXISTS idx_sync_logs_kitchen_started
    ON sync_logs(kitchen_id, started_at DESC);

-- Kitchen users
CREATE INDEX IF NOT EXISTS idx_kitchen_users_kitchen_active
    ON kitchen_users(kitchen_id, is_active) WHERE is_active = TRUE;

INSERT INTO schema_migrations (version)
VALUES ('005_performance_indexes')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 005 applied!' AS status;