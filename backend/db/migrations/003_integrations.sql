-- ============================================================
-- KitchenIQ — Migration 003: Integrations + Sync Logs
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS integrations (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'disconnected',
    auth_type VARCHAR(50) DEFAULT 'mock',
    last_sync_at TIMESTAMP,
    last_successful_sync TIMESTAMP,
    last_error TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(kitchen_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_integrations_kitchen ON integrations(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_integrations_status ON integrations(status);

CREATE TABLE IF NOT EXISTS sync_logs (
    id SERIAL PRIMARY KEY,
    integration_id INTEGER NOT NULL REFERENCES integrations(id) ON DELETE CASCADE,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    records_fetched INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    duration_seconds NUMERIC(10, 2)
);

CREATE INDEX IF NOT EXISTS idx_sync_logs_integration ON sync_logs(integration_id, started_at DESC);

INSERT INTO schema_migrations (version)
VALUES ('003_integrations')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 003 applied!' AS status;