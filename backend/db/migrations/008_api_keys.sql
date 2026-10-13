-- Migration 008: API Keys
BEGIN;

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    scopes VARCHAR(255) NOT NULL DEFAULT 'read',
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

INSERT INTO schema_migrations (version)
VALUES ('008_api_keys')
ON CONFLICT (version) DO NOTHING;

COMMIT;
SELECT 'Migration 008 applied!' AS status;