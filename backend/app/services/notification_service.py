"""
KitchenIQ — Notification Service
Create + manage in-app notifications.
"""
from db.connection import execute_query, execute_one


def create_notification(user_id, kitchen_id, type, title,
                        message=None, severity='info', link=None):
    """Insert a notification. Returns ID or None."""
    try:
        row = execute_one(
            """
            INSERT INTO notifications
                (user_id, kitchen_id, type, severity, title, message, link)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, kitchen_id, type, severity, title, message, link),
        )
        return row['id'] if row else None
    except Exception as e:
        print(f"[notif] create failed: {e}")
        return None


def notify_kitchen_owner(kitchen_id, type, title, message=None,
                         severity='info', link=None):
    """Find kitchen owner and notify them."""
    kitchen = execute_one(
        "SELECT user_id FROM kitchens WHERE id = %s",
        (kitchen_id,),
    )
    if not kitchen:
        return None
    return create_notification(
        user_id=kitchen['user_id'],
        kitchen_id=kitchen_id,
        type=type,
        title=title,
        message=message,
        severity=severity,
        link=link,
    )


# Event helpers
def notify_sync_success(kitchen_id, platform, created):
    if created <= 0:
        return None
    return notify_kitchen_owner(
        kitchen_id,
        type='sync_success',
        title=f"{created} new order{'s' if created > 1 else ''} from {platform.capitalize()}",
        message='Dashboard updated with latest data.',
        severity='success',
        link='/pages/dashboard.html',
    )


def notify_sync_failed(kitchen_id, platform, error):
    return notify_kitchen_owner(
        kitchen_id,
        type='sync_failed',
        title=f"{platform.capitalize()} sync failed",
        message=str(error)[:300],
        severity='danger',
        link='/pages/integrations.html',
    )


def notify_insight(kitchen_id, title, message, severity='warning'):
    return notify_kitchen_owner(
        kitchen_id,
        type='insight',
        title=title,
        message=message,
        severity=severity,
        link='/pages/insights.html',
    )