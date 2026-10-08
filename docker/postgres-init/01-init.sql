-- ============================================================
-- KitchenIQ — Postgres Init (runs on first container start)
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Timezone
SET timezone = 'Asia/Kolkata';

-- Success marker
SELECT 'KitchenIQ Postgres initialized' AS status;
