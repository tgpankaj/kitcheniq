"""
KitchenIQ — Database Connection (Robust)
Thread-safe connection pool with safe release.
"""
import os
import threading
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

_pool = None
_pool_lock = threading.Lock()


def init_pool():
    """Initialize connection pool (thread-safe, once only)."""
    global _pool

    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        dsn = os.getenv('DATABASE_URL')
        if not dsn:
            raise ValueError("DATABASE_URL not set in .env")

        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=dsn,
        )
        print("[db] Connection pool initialized")
        return _pool


def get_conn():
    """Get a connection from pool."""
    p = init_pool()
    return p.getconn()


def release_conn(conn):
    """Safely return connection to pool."""
    if conn is None:
        return

    p = _pool
    if p is None:
        return

    try:
        p.putconn(conn)
    except Exception as e:
        # Silent fail if already released
        print(f"[db] release_conn warning: {e}")


def execute_query(query, params=None, fetch=True):
    """Execute a query and return rows (if fetch) or True."""
    conn = None
    cur = None

    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params or ())

        if fetch:
            result = cur.fetchall()
            conn.commit()
            return result
        else:
            conn.commit()
            return True

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise e

    finally:
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            release_conn(conn)


def execute_one(query, params=None):
    """Execute and return first row."""
    result = execute_query(query, params, fetch=True)
    return result[0] if result else None