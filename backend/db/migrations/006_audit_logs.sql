-- ============================================================
-- KitchenIQ — Migration 006: Audit Logs
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    resource VARCHAR(100),
    resource_id VARCHAR(100),
    description TEXT,
    metadata JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_kitchen ON audit_logs(kitchen_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_category ON audit_logs(category, created_at DESC);

INSERT INTO schema_migrations (version)
VALUES ('006_audit_logs')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 006 applied!' AS status;
