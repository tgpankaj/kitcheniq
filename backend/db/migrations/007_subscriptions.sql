-- ============================================================
-- KitchenIQ — Migration 007: Subscriptions (SaaS Billing)
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL DEFAULT 'free',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    razorpay_order_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_plan ON subscriptions(plan);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at);

INSERT INTO schema_migrations (version)
VALUES ('007_subscriptions')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 007 applied!' AS status;
