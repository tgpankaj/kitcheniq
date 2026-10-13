#!/bin/bash
# ============================================================
# KitchenIQ — Backend Entrypoint
# ============================================================
set -e

echo "🐳 KitchenIQ Backend starting..."

# Wait for database
if [ -n "$DATABASE_URL" ]; then
    echo "⏳ Waiting for database..."
    python -c "
import os, sys, time
import psycopg2
dsn = os.getenv('DATABASE_URL')
for i in range(30):
    try:
        conn = psycopg2.connect(dsn)
        conn.close()
        print('✅ Database ready')
        sys.exit(0)
    except Exception as e:
        print(f'  attempt {i+1}/30: {type(e).__name__}')
        time.sleep(2)
print('❌ Database not reachable after 60s')
sys.exit(1)
"
fi

# Run migrations
echo "📦 Running migrations..."
SCRIPT="/app/backend/scripts/run_migration.py"
[ ! -f "$SCRIPT" ] && SCRIPT="/app/scripts/run_migration.py"
[ ! -f "$SCRIPT" ] && SCRIPT="./scripts/run_migration.py"

if [ -f "$SCRIPT" ]; then
    python "$SCRIPT" up 000_init || true
    python "$SCRIPT" up 001_core_schema || true
    python "$SCRIPT" up 002_ingredients_recipes || true
    python "$SCRIPT" up 003_integrations || true
    python "$SCRIPT" up 004_notifications || true
    python "$SCRIPT" up 005_performance_indexes || true
    python "$SCRIPT" up 006_audit_logs || true
    python "$SCRIPT" up 007_subscriptions || true
    python "$SCRIPT" up 008_api_keys || true
    echo "✅ Migrations done"
fi

# Start Gunicorn
echo "🚀 Starting Gunicorn..."
exec gunicorn -c gunicorn.conf.py run:app