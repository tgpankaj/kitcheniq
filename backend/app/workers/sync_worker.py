"""
KitchenIQ — Auto-Sync Worker

Runs every N minutes and syncs all connected integrations
across all kitchens using APScheduler.

No Redis needed for MVP — runs inside Flask process.
"""
import logging
from datetime import datetime, timedelta

from db.connection import execute_query
from app.services.sync_service import SyncService
from app.services.integrations.mock import MockIntegration


logger = logging.getLogger(__name__)

_scheduler = None


# ============================================================
# AUTO-SYNC ALL
# ============================================================

def auto_sync_all():
    """Find connected integrations and sync stale ones."""
    logger.info("[worker] auto_sync_all started")

    integrations = execute_query(
        """
        SELECT i.id, i.kitchen_id, i.platform, i.last_sync_at
        FROM integrations i
        WHERE i.status = 'connected'
          AND i.is_active = TRUE
          AND (
              i.last_sync_at IS NULL
              OR i.last_sync_at < NOW() - INTERVAL '4 minutes'
          )
        ORDER BY i.last_sync_at NULLS FIRST
        LIMIT 20
        """
    )

    if not integrations:
        logger.info("[worker] no stale integrations")
        return {'synced': 0, 'failed': 0, 'total': 0}

    synced = 0
    failed = 0

    for integ in integrations:
        try:
            _sync_one(integ)
            synced += 1
        except Exception as e:
            logger.error(f"[worker] sync failed for integ {integ['id']}: {e}")
            failed += 1

    logger.info(f"[worker] done — synced={synced} failed={failed}")
    return {'synced': synced, 'failed': failed, 'total': len(integrations)}


def _sync_one(integ):
    """Sync a single integration row."""
    platform = integ['platform']
    kitchen_id = integ['kitchen_id']

    logger.info(f"[worker] syncing kitchen={kitchen_id} platform={platform}")

    # Build mock integration (real provider later)
    if platform in ('zomato', 'swiggy', 'pos', 'website'):
        mock = MockIntegration(kitchen_id, platform=platform)
        mock.connect()
    else:
        raise ValueError(f"Unknown platform: {platform}")

    # Sync last 15 orders (dedup will skip existing)
    service = SyncService(integ['id'], kitchen_id, platform)
    result = service.run(mock, count=15)

    logger.info(f"[worker] result: {result}")
    return result




# ============================================================
# WEEKLY DIGEST
# ============================================================

def send_weekly_digests():
    """Send weekly summary email to all users. Runs every Monday 9 AM."""
    logger.info("[worker] send_weekly_digests started")

    users = execute_query(
        """
        SELECT u.id AS user_id, u.email, u.full_name,
               k.id AS kitchen_id, k.name AS kitchen_name
        FROM users u
        JOIN kitchens k ON k.user_id = u.id
        WHERE k.is_active = TRUE
        """
    )

    sent = 0
    failed = 0

    from app.services import email_service

    for u in users:
        try:
            # Last 7 days stats
            stats = execute_one(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
                    COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue,
                    COALESCE(SUM(profit) FILTER (WHERE status != 'cancelled'), 0) AS profit,
                    COALESCE(AVG(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS aov
                FROM orders
                WHERE kitchen_id = %s
                  AND order_date >= CURRENT_DATE - INTERVAL '7 days'
                """,
                (u['kitchen_id'],),
            )

            email_service.send_weekly_digest(
                u['user_id'], u['email'], u['kitchen_name'],
                {
                    'orders': int(stats['orders']) if stats else 0,
                    'revenue': float(stats['revenue']) if stats else 0,
                    'profit': float(stats['profit']) if stats else 0,
                    'aov': float(stats['aov']) if stats else 0,
                },
            )
            sent += 1
        except Exception as e:
            logger.error(f"[worker] digest failed for {u['email']}: {e}")
            failed += 1

    logger.info(f"[worker] send_weekly_digests done — sent={sent} failed={failed}")
    return {'sent': sent, 'failed': failed}


# ============================================================
# SCHEDULER
# ============================================================

def start_scheduler(app, interval_minutes=5):
    """Start background scheduler. Idempotent."""
    global _scheduler

    if _scheduler is not None:
        logger.info("[worker] scheduler already running")
        return _scheduler

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BackgroundScheduler(daemon=True)

    def _job():
        with app.app_context():
            try:
                auto_sync_all()
            except Exception as e:
                logger.error(f"[worker] job error: {e}")

    scheduler.add_job(
        _job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id='auto_sync_all',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    _scheduler = scheduler

    logger.info(f"[worker] scheduler started — every {interval_minutes} min")
    return scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[worker] scheduler stopped")


def scheduler_status():
    """Return current scheduler state (for API)."""
    if _scheduler is None:
        return {'running': False, 'jobs': []}

    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            'id': job.id,
            'next_run': str(next_run) if next_run else None,
        })

    return {'running': True, 'jobs': jobs}