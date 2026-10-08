"""
KitchenIQ — Notifications Routes
GET    /api/notifications/           (list)
GET    /api/notifications/unread-count
POST   /api/notifications/<id>/read
POST   /api/notifications/read-all
DELETE /api/notifications/<id>
POST   /api/notifications/test       (create sample)
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.services.notification_service import create_notification


notifications_bp = Blueprint('notifications', __name__)


def get_kitchen_id(user_id):
    from app.utils.kitchen_context import get_current_kitchen_id
    return get_current_kitchen_id(user_id)


# ============================================================
# LIST
# ============================================================

@notifications_bp.route('/', methods=['GET'])
@token_required
def list_all():
    limit = min(int(request.args.get('limit', 20)), 100)
    unread_only = request.args.get('unread') == '1'

    where = ['user_id = %s']
    params = [request.user_id]

    if unread_only:
        where.append('is_read = FALSE')

    rows = execute_query(
        f"""
        SELECT id, type, severity, title, message, link, is_read, created_at
        FROM notifications
        WHERE {' AND '.join(where)}
        ORDER BY created_at DESC
        LIMIT %s
        """,
        tuple(params + [limit]),
    )

    return jsonify([
        {
            'id': r['id'],
            'type': r['type'],
            'severity': r['severity'],
            'title': r['title'],
            'message': r['message'],
            'link': r['link'],
            'is_read': r['is_read'],
            'created_at': str(r['created_at']) if r['created_at'] else None,
        }
        for r in rows
    ])


# ============================================================
# UNREAD COUNT
# ============================================================

@notifications_bp.route('/unread-count', methods=['GET'])
@token_required
def unread_count():
    row = execute_one(
        "SELECT COUNT(*)::int AS c FROM notifications WHERE user_id = %s AND is_read = FALSE",
        (request.user_id,),
    )
    return jsonify({'unread': row['c'] if row else 0})


# ============================================================
# MARK READ
# ============================================================

@notifications_bp.route('/<int:nid>/read', methods=['POST'])
@token_required
def mark_read(nid):
    execute_query(
        "UPDATE notifications SET is_read = TRUE WHERE id = %s AND user_id = %s",
        (nid, request.user_id),
        fetch=False,
    )
    return jsonify({'ok': True})


@notifications_bp.route('/read-all', methods=['POST'])
@token_required
def mark_all():
    execute_query(
        "UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND is_read = FALSE",
        (request.user_id,),
        fetch=False,
    )
    return jsonify({'ok': True})


# ============================================================
# DELETE
# ============================================================

@notifications_bp.route('/<int:nid>', methods=['DELETE'])
@token_required
def delete_one(nid):
    execute_query(
        "DELETE FROM notifications WHERE id = %s AND user_id = %s",
        (nid, request.user_id),
        fetch=False,
    )
    return jsonify({'ok': True})


# ============================================================
# TEST (create sample notification)
# ============================================================

@notifications_bp.route('/test', methods=['POST'])
@token_required
def test_create():
    kitchen_id = get_kitchen_id(request.user_id)
    create_notification(
        user_id=request.user_id,
        kitchen_id=kitchen_id,
        type='test',
        title='Test notification',
        message='If you see this, notifications are working!',
        severity='info',
    )
    return jsonify({'ok': True})