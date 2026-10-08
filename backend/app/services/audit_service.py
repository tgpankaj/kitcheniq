"""
KitchenIQ — Audit Service
Central place to log user actions.
"""
from flask import request

from db.connection import execute_query


# ============================================================
# CORE
# ============================================================

def log_action(user_id, kitchen_id, action, category="general",
               resource=None, resource_id=None, description=None, metadata=None):
    """
    Log an audit action.

    Categories: auth, order, integration, team, settings, data, system
    Actions:   login, signup, order_create, sync_success, member_added, etc.
    """
    try:
        ip = None
        ua = None

        try:
            ip = request.remote_addr
            ua = request.headers.get("User-Agent", "")[:500]
        except RuntimeError:
            # Outside request context
            pass

        execute_query(
            """
            INSERT INTO audit_logs
                (user_id, kitchen_id, action, category, resource, resource_id,
                 description, metadata, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, kitchen_id, action, category, resource, resource_id,
             description, metadata, ip, ua),
            fetch=False,
        )
    except Exception as e:
        # Never crash the main flow due to audit failure
        print(f"[audit] log failed: {e}")


# ============================================================
# CONVENIENCE HELPERS
# ============================================================

def log_login(user_id, kitchen_id=None, success=True):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="login" if success else "login_failed",
        category="auth",
        description="User logged in" if success else "Login attempt failed",
    )


def log_signup(user_id, kitchen_id=None, email=None):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="signup",
        category="auth",
        description=f"New account created: {email or 'unknown'}",
    )


def log_order_created(user_id, kitchen_id, order_id, amount, platform):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="order_create",
        category="order",
        resource="order",
        resource_id=str(order_id),
        description=f"Order #{order_id} created (Rs.{amount}) via {platform}",
    )


def log_sync_success(user_id, kitchen_id, platform, created, updated):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="sync_success",
        category="integration",
        resource="integration",
        resource_id=platform,
        description=f"{platform.capitalize()} sync: {created} new, {updated} updated",
    )


def log_sync_failed(user_id, kitchen_id, platform, error):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="sync_failed",
        category="integration",
        resource="integration",
        resource_id=platform,
        description=f"{platform.capitalize()} sync failed: {str(error)[:200]}",
    )


def log_member_added(user_id, kitchen_id, new_member_email, role):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="member_added",
        category="team",
        resource="user",
        description=f"Added {new_member_email} as {role}",
    )


def log_member_removed(user_id, kitchen_id, member_email):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="member_removed",
        category="team",
        resource="user",
        description=f"Removed {member_email} from team",
    )


def log_kitchen_created(user_id, kitchen_id, name):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="kitchen_created",
        category="settings",
        resource="kitchen",
        resource_id=str(kitchen_id),
        description=f"Created kitchen: {name}",
    )


def log_kitchen_updated(user_id, kitchen_id, name):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="kitchen_updated",
        category="settings",
        resource="kitchen",
        resource_id=str(kitchen_id),
        description=f"Updated kitchen: {name}",
    )


def log_data_upload(user_id, kitchen_id, filename, rows_created, rows_failed):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="csv_upload",
        category="data",
        resource="upload",
        description=f"Uploaded {filename}: {rows_created} created, {rows_failed} failed",
    )


def log_export(user_id, kitchen_id, export_type, days):
    log_action(
        user_id=user_id,
        kitchen_id=kitchen_id,
        action="export",
        category="data",
        resource="report",
        resource_id=export_type,
        description=f"Exported {export_type} report ({days} days)",
    )
