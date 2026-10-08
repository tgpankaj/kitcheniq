"""
KitchenIQ — Audit Routes (Fixed)
"""
from flask import Blueprint, request, jsonify
from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.utils.kitchen_context import get_current_kitchen_id


audit_bp = Blueprint('audit', __name__)


def _i(v):
    try:
        return int(v or 0)
    except (ValueError, TypeError):
        return 0


@audit_bp.route('/', methods=['GET'])
@token_required
def list_logs():
    kitchen_id = get_current_kitchen_id(request.user_id)

    limit = min(int(request.args.get('limit', 50)), 200)
    category = request.args.get('category')
    action = request.args.get('action')
    days = request.args.get('days')

    where = []
    params = []

    # Ownership: user's logs OR logs from user's kitchens
    where.append('(a.user_id = %s OR a.kitchen_id IN (SELECT id FROM kitchens WHERE user_id = %s))')
    params.extend([request.user_id, request.user_id])

    # If current kitchen selected, filter by it
    if kitchen_id:
        where.append('(a.kitchen_id = %s OR a.kitchen_id IS NULL)')
        params.append(kitchen_id)

    if category:
        where.append('a.category = %s')
        params.append(category)

    if action:
        where.append('a.action = %s')
        params.append(action)

    if days:
        try:
            d = int(days)
            where.append("a.created_at >= NOW() - INTERVAL '%s days'")
            params.append(d)
        except (ValueError, TypeError):
            pass

    params.append(limit)

    rows = execute_query(
        f"""
        SELECT
            a.id, a.action, a.category, a.resource, a.resource_id,
            a.description, a.metadata, a.ip_address, a.created_at,
            u.email AS user_email, u.full_name AS user_name,
            k.name AS kitchen_name
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.user_id
        LEFT JOIN kitchens k ON k.id = a.kitchen_id
        WHERE {' AND '.join(where)}
        ORDER BY a.created_at DESC
        LIMIT %s
        """,
        tuple(params),
    )

    return jsonify([
        {
            'id': r['id'],
            'action': r['action'],
            'category': r['category'],
            'resource': r['resource'],
            'resource_id': r['resource_id'],
            'description': r['description'],
            'metadata': str(r['metadata']) if r['metadata'] else None,
            'ip': r['ip_address'],
            'created_at': str(r['created_at']) if r['created_at'] else None,
            'user': {
                'email': r['user_email'],
                'name': r['user_name'] or (r['user_email'].split('@')[0] if r['user_email'] else 'System'),
            } if r['user_email'] else {'name': 'System'},
            'kitchen': r['kitchen_name'],
        }
        for r in rows
    ])


@audit_bp.route('/summary', methods=['GET'])
@token_required
def summary():
    kitchen_id = get_current_kitchen_id(request.user_id)

    where = ['(a.user_id = %s OR a.kitchen_id IN (SELECT id FROM kitchens WHERE user_id = %s))']
    params = [request.user_id, request.user_id]

    if kitchen_id:
        where.append('(a.kitchen_id = %s OR a.kitchen_id IS NULL)')
        params.append(kitchen_id)

    rows = execute_query(
        f"""
        SELECT a.category, COUNT(*)::int AS c
        FROM audit_logs a
        WHERE {' AND '.join(where)}
          AND a.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY a.category
        ORDER BY c DESC
        """,
        tuple(params),
    )

    total = execute_one(
        f"SELECT COUNT(*)::int AS c FROM audit_logs a WHERE {' AND '.join(where)}",
        tuple(params),
    )

    return jsonify({
        'total': _i(total['c']) if total else 0,
        'by_category': {r['category']: r['c'] for r in rows},
    })


@audit_bp.route('/actions', methods=['GET'])
@token_required
def actions():
    kitchen_id = get_current_kitchen_id(request.user_id)

    where = ['(a.user_id = %s OR a.kitchen_id IN (SELECT id FROM kitchens WHERE user_id = %s))']
    params = [request.user_id, request.user_id]

    if kitchen_id:
        where.append('(a.kitchen_id = %s OR a.kitchen_id IS NULL)')
        params.append(kitchen_id)

    rows = execute_query(
        f"""
        SELECT DISTINCT a.action FROM audit_logs a
        WHERE {' AND '.join(where)}
        ORDER BY a.action
        """,
        tuple(params),
    )

    return jsonify([r['action'] for r in rows])
