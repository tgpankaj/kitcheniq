"""
KitchenIQ — Integrations Routes
GET    /api/integrations/           (list)
POST   /api/integrations/connect    {platform}
POST   /api/integrations/disconnect {platform}
POST   /api/integrations/sync       {platform, count?}
GET    /api/integrations/<id>/logs
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.services.integrations.mock import MockIntegration
from app.services.sync_service import SyncService


integrations_bp = Blueprint('integrations', __name__)


SUPPORTED = ('zomato', 'swiggy', 'pos', 'website')


def get_kitchen_id(user_id):
    from app.utils.kitchen_context import get_current_kitchen_id
    return get_current_kitchen_id(user_id)


# ============================================================
# LIST
# ============================================================

@integrations_bp.route('/', methods=['GET'])
@token_required
def list_all():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    rows = execute_query(
        """
        SELECT id, platform, status, last_sync_at, last_successful_sync, last_error
        FROM integrations
        WHERE kitchen_id = %s
        ORDER BY platform
        """,
        (kitchen_id,),
    )

    return jsonify([
        {
            'id': r['id'],
            'platform': r['platform'],
            'status': r['status'],
            'last_sync_at': str(r['last_sync_at']) if r['last_sync_at'] else None,
            'last_successful_sync': str(r['last_successful_sync']) if r['last_successful_sync'] else None,
            'last_error': r['last_error'],
        }
        for r in rows
    ])


# ============================================================
# CONNECT
# ============================================================

@integrations_bp.route('/connect', methods=['POST'])
@token_required
def connect():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    d = request.get_json() or {}
    platform = (d.get('platform') or '').lower().strip()

    if platform not in SUPPORTED:
        return jsonify({'error': f'Unsupported platform: {platform}'}), 400

    existing = execute_one(
        "SELECT id, status FROM integrations WHERE kitchen_id = %s AND platform = %s",
        (kitchen_id, platform),
    )

    if existing and existing['status'] == 'connected':
        return jsonify({'message': 'Already connected', 'id': existing['id']})

    if existing:
        execute_query(
            """
            UPDATE integrations
            SET status = 'connected', last_error = NULL, updated_at = NOW()
            WHERE id = %s
            """,
            (existing['id'],),
            fetch=False,
        )
        integration_id = existing['id']
    else:
        row = execute_one(
            """
            INSERT INTO integrations (kitchen_id, platform, status, auth_type)
            VALUES (%s, %s, 'connected', 'mock')
            RETURNING id
            """,
            (kitchen_id, platform),
        )
        integration_id = row['id']

    return jsonify({
        'message': f'{platform.capitalize()} connected',
        'id': integration_id,
        'platform': platform,
        'status': 'connected',
    }), 201


# ============================================================
# DISCONNECT
# ============================================================

@integrations_bp.route('/disconnect', methods=['POST'])
@token_required
def disconnect():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    d = request.get_json() or {}
    platform = (d.get('platform') or '').lower().strip()

    existing = execute_one(
        "SELECT id FROM integrations WHERE kitchen_id = %s AND platform = %s",
        (kitchen_id, platform),
    )
    if not existing:
        return jsonify({'error': 'Integration not found'}), 404

    execute_query(
        "UPDATE integrations SET status = 'disconnected', updated_at = NOW() WHERE id = %s",
        (existing['id'],),
        fetch=False,
    )

    return jsonify({'message': f'{platform.capitalize()} disconnected'})


# ============================================================
# SYNC
# ============================================================

@integrations_bp.route('/sync', methods=['POST'])
@token_required
def sync():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    d = request.get_json() or {}
    platform = (d.get('platform') or '').lower().strip()
    count = min(int(d.get('count', 15)), 50)

    integration = execute_one(
        "SELECT id, status FROM integrations WHERE kitchen_id = %s AND platform = %s",
        (kitchen_id, platform),
    )

    if not integration:
        return jsonify({
            'error': f'{platform.capitalize()} not connected',
            'hint': 'Call /connect first',
        }), 400

    if integration['status'] != 'connected':
        return jsonify({'error': f'Integration is {integration["status"]}'}), 400

    # Run sync
    mock = MockIntegration(kitchen_id, platform=platform)
    mock.connect()

    service = SyncService(integration['id'], kitchen_id, platform)
    result = service.run(mock, count=count)

    return jsonify({'platform': platform, **result})


# ============================================================
# LOGS
# ============================================================

@integrations_bp.route('/<int:iid>/logs', methods=['GET'])
@token_required
def logs(iid):
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    integration = execute_one(
        "SELECT id FROM integrations WHERE id = %s AND kitchen_id = %s",
        (iid, kitchen_id),
    )
    if not integration:
        return jsonify({'error': 'Integration not found'}), 404

    limit = min(int(request.args.get('limit', 20)), 100)

    rows = execute_query(
        """
        SELECT id, status, started_at, completed_at,
               records_fetched, records_created, records_updated, records_failed,
               error_message, duration_seconds
        FROM sync_logs
        WHERE integration_id = %s
        ORDER BY started_at DESC
        LIMIT %s
        """,
        (iid, limit),
    )

    return jsonify([
        {
            'id': r['id'],
            'status': r['status'],
            'started_at': str(r['started_at']) if r['started_at'] else None,
            'completed_at': str(r['completed_at']) if r['completed_at'] else None,
            'fetched': r['records_fetched'],
            'created': r['records_created'],
            'updated': r['records_updated'],
            'failed': r['records_failed'],
            'error': r['error_message'],
            'duration': float(r['duration_seconds']) if r['duration_seconds'] else None,
        }
        for r in rows
    ])