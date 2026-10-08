-- ============================================================
-- KitchenIQ — Migration 000: Tracking Table
-- ============================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(100) NOT NULL UNIQUE,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
);

SELECT 'Migration tracking table ready!' AS status;