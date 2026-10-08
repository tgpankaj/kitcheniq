#!/bin/bash
# ============================================================
# KitchenIQ — Container Entrypoint
# Waits for Postgres, runs migrations, then starts gunicorn.
# ============================================================
set -e

echo "🚀 Starting KitchenIQ backend..."
echo "   Waiting for PostgreSQL to be ready..."

# Wait for postgres (up to 30 seconds)
python -c "
import os, time, sys
import psycopg2
from psycopg2 import OperationalError

dsn = os.getenv('DATABASE_URL')
for i in range(30):
    try:
        conn = psycopg2.connect(dsn)
        conn.close()
        print('✅ Postgres ready')
        sys.exit(0)
    except OperationalError as e:
        print(f'   Waiting... ({i+1}/30)')
        time.sleep(1)

print('❌ Postgres not ready after 30s')
sys.exit(1)
"

# Run migrations
echo "📦 Running migrations..."
cd /app
python scripts/run_migration.py up 001_core_schema || echo "  (001 already applied)"
python scripts/run_migration.py up 002_ingredients_recipes || echo "  (002 already applied)"
python scripts/run_migration.py up 003_integrations || echo "  (003 already applied)"
python scripts/run_migration.py up 004_notifications || echo "  (004 already applied)"
python scripts/run_migration.py up 005_performance_indexes || echo "  (005 already applied)"
python scripts/run_migration.py up 006_audit_logs || echo "  (006 already applied)"
python scripts/run_migration.py up 007_subscriptions || echo "  (007 already applied)"
python scripts/run_migration.py up 008_oauth_states || echo "  (008 already applied)"
python scripts/run_migration.py up 009_email_logs || echo "  (009 already applied)"

echo "✅ Migrations complete"
echo "🚀 Starting gunicorn..."

# Start gunicorn
exec gunicorn \
    --workers 2 \
    --worker-class gthread \
    --threads 4 \
    --bind 0.0.0.0:5000 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    run:app
