-- ============================================================
-- KitchenIQ — Migration 009: Email Logs
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    to_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    template VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'sent',
    provider_id VARCHAR(255),
    error_message TEXT,
    metadata JSONB,
    sent_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_logs_user ON email_logs(user_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_template ON email_logs(template, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status, sent_at DESC);

-- Email preferences (opt-in/opt-out)
CREATE TABLE IF NOT EXISTS email_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    welcome_email BOOLEAN DEFAULT TRUE,
    payment_receipts BOOLEAN DEFAULT TRUE,
    weekly_digest BOOLEAN DEFAULT TRUE,
    sync_alerts BOOLEAN DEFAULT TRUE,
    marketing BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO schema_migrations (version)
VALUES ('009_email_logs')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 009 applied!' AS status;
