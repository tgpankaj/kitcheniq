"""
KitchenIQ — Migration Runner

Usage:
    python scripts/run_migration.py up 001_core_schema
    python scripts/run_migration.py list
    python scripts/run_migration.py status
"""
import os
import sys
from pathlib import Path

# Path setup
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


MIGRATIONS_DIR = BACKEND_DIR / "db" / "migrations"


def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL not set in backend/.env")
        sys.exit(1)
    conn = psycopg2.connect(dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def read_sql(filename):
    path = MIGRATIONS_DIR / filename
    if not path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def apply_migration(version):
    filename = f"{version}.sql"
    sql = read_sql(filename)

    print(f"\n📦 Applying: {filename}")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql)

        # Print status messages
        try:
            for row in cur.fetchall():
                print(f"   → {row}")
        except psycopg2.ProgrammingError:
            pass

        print(f"✅ Applied: {version}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


def list_migrations():
    print("\n📁 Available migrations:\n")
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        print(f"   • {f.name}")


def show_status():
    print("\n📊 Migration Status:\n")
    conn = get_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT version, applied_at FROM schema_migrations ORDER BY id")
            rows = cur.fetchall()
            if not rows:
                print("   No migrations applied yet.")
            for v, t in rows:
                print(f"   ✅ {v}   ({t})")
        except psycopg2.errors.UndefinedTable:
            print("   ⚠️  schema_migrations table does not exist.")
            print("   Run: python scripts/run_migration.py up 000_init")
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    if action == "up":
        if len(sys.argv) < 3:
            print("❌ Usage: python run_migration.py up <version>")
            sys.exit(1)
        apply_migration(sys.argv[2])

    elif action == "list":
        list_migrations()

    elif action == "status":
        show_status()

    else:
        print(f"❌ Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()