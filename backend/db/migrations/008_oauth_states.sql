-- ============================================================
-- KitchenIQ — Migration 008: OAuth States (CSRF protection)
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS oauth_states (
    id SERIAL PRIMARY KEY,
    state VARCHAR(255) NOT NULL UNIQUE,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_oauth_states_state ON oauth_states(state);
CREATE INDEX IF NOT EXISTS idx_oauth_states_created ON oauth_states(created_at DESC);

INSERT INTO schema_migrations (version)
VALUES ('008_oauth_states')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 008 applied!' AS status;
