import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import psycopg2
from psycopg2.extras import RealDictCursor

database_url = os.getenv("DATABASE_URL")

if not database_url:
    print("❌ DATABASE_URL not found in .env")
    sys.exit(1)

print("🔌 Connecting to PostgreSQL...")

try:
    conn = psycopg2.connect(database_url)
    print("✅ Database connection successful\n")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    tables = [r["table_name"] for r in cur.fetchall()]

    print("=== TABLES IN DATABASE ===\n")

    for table in tables:
        # Safe identifier quoting
        cur.execute(
            'SELECT COUNT(*) AS c FROM "{}"'.format(table.replace('"', '""'))
        )
        count = cur.fetchone()["c"]
        print(f"  ✅ {table:30} ({count} rows)")

    print(f"\n✅ Total: {len(tables)} tables")

    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Database verification failed:")
    print(f"   {e}")
    sys.exit(1)