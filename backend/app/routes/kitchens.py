"""
KitchenIQ — Kitchens Routes (Multi-Branch)
GET  /api/kitchens/              list all kitchens of user
POST /api/kitchens/              create new kitchen/branch
GET  /api/kitchens/<id>          get kitchen details
PUT  /api/kitchens/<id>          update kitchen
DELETE /api/kitchens/<id>        soft delete
GET  /api/kitchens/<id>/stats    per-kitchen stats
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.services import audit_service


kitchens_bp = Blueprint('kitchens', __name__)


def _i(v):
    try:
        return int(v or 0)
    except (ValueError, TypeError):
        return 0


def _f(v):
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


# ============================================================
# LIST
# ============================================================

@kitchens_bp.route('/', methods=['GET'])
@token_required
def list_kitchens():
    rows = execute_query(
        """
        SELECT
            k.id, k.name, k.city, k.address, k.phone, k.is_active,
            k.created_at,
            (SELECT COUNT(*)::int FROM orders WHERE kitchen_id = k.id) AS total_orders,
            (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE kitchen_id = k.id AND status != 'cancelled') AS total_revenue
        FROM kitchens k
        WHERE k.user_id = %s
        ORDER BY k.id
        """,
        (request.user_id,),
    )

    return jsonify([
        {
            'id': r['id'],
            'name': r['name'],
            'city': r['city'],
            'address': r['address'],
            'phone': r['phone'],
            'is_active': r['is_active'],
            'created_at': str(r['created_at']) if r['created_at'] else None,
            'total_orders': _i(r['total_orders']),
            'total_revenue': round(_f(r['total_revenue']), 2),
        }
        for r in rows
    ])


# ============================================================
# CREATE
# ============================================================

@kitchens_bp.route('/', methods=['POST'])
@token_required
def create_kitchen():
    d = request.get_json() or {}
    name = (d.get('name') or '').strip()

    if not name:
        return jsonify({'error': 'Kitchen name is required'}), 400

    row = execute_one(
        """
        INSERT INTO kitchens (user_id, name, city, address, phone)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, name
        """,
        (
            request.user_id,
            name,
            d.get('city'),
            d.get('address'),
            d.get('phone'),
        ),
    )

    # Add owner to kitchen_users
    execute_query(
        """
        INSERT INTO kitchen_users (kitchen_id, user_id, role, accepted_at)
        VALUES (%s, %s, 'owner', NOW())
        ON CONFLICT (kitchen_id, user_id) DO NOTHING
        """,
        (row['id'], request.user_id),
        fetch=False,
    )

    try:
        audit_service.log_kitchen_created(request.user_id, row['id'], row['name'])
    except Exception:
        pass

    return jsonify({
        'message': 'Kitchen created',
        'id': row['id'],
        'name': row['name'],
    }), 201


# ============================================================
# GET ONE
# ============================================================

@kitchens_bp.route('/<int:kid>', methods=['GET'])
@token_required
def get_kitchen(kid):
    k = execute_one(
        "SELECT * FROM kitchens WHERE id = %s AND user_id = %s",
        (kid, request.user_id),
    )
    if not k:
        return jsonify({'error': 'Kitchen not found'}), 404

    return jsonify({
        'id': k['id'],
        'name': k['name'],
        'city': k['city'],
        'address': k['address'],
        'phone': k['phone'],
        'timezone': k['timezone'],
        'currency': k['currency'],
        'is_active': k['is_active'],
    })


# ============================================================
# UPDATE
# ============================================================

@kitchens_bp.route('/<int:kid>', methods=['PUT'])
@token_required
def update_kitchen(kid):
    existing = execute_one(
        "SELECT id FROM kitchens WHERE id = %s AND user_id = %s",
        (kid, request.user_id),
    )
    if not existing:
        return jsonify({'error': 'Kitchen not found'}), 404

    d = request.get_json() or {}

    execute_query(
        """
        UPDATE kitchens
        SET name = COALESCE(NULLIF(%s, ''), name),
            city = %s,
            address = %s,
            phone = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (d.get('name', ''), d.get('city'), d.get('address'), d.get('phone'), kid),
        fetch=False,
    )

    return jsonify({'message': 'Updated'})


# ============================================================
# DELETE (soft)
# ============================================================

@kitchens_bp.route('/<int:kid>', methods=['DELETE'])
@token_required
def delete_kitchen(kid):
    # Cannot delete last kitchen
    count = execute_one(
        "SELECT COUNT(*)::int AS c FROM kitchens WHERE user_id = %s AND is_active = TRUE",
        (request.user_id,),
    )
    if count and count['c'] <= 1:
        return jsonify({'error': 'Cannot delete your only kitchen'}), 400

    execute_query(
        "UPDATE kitchens SET is_active = FALSE WHERE id = %s AND user_id = %s",
        (kid, request.user_id),
        fetch=False,
    )

    return jsonify({'message': 'Kitchen deleted'})


# ============================================================
# STATS
# ============================================================

@kitchens_bp.route('/<int:kid>/stats', methods=['GET'])
@token_required
def stats(kid):
    # Verify ownership
    k = execute_one(
        "SELECT id, name FROM kitchens WHERE id = %s AND user_id = %s",
        (kid, request.user_id),
    )
    if not k:
        return jsonify({'error': 'Kitchen not found'}), 404

    row = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue,
            COALESCE(SUM(profit) FILTER (WHERE status != 'cancelled'), 0) AS profit,
            COUNT(DISTINCT customer_phone) FILTER (WHERE customer_phone IS NOT NULL) AS customers
        FROM orders
        WHERE kitchen_id = %s
        """,
        (kid,),
    )

    return jsonify({
        'kitchen_id': kid,
        'kitchen_name': k['name'],
        'total_orders': _i(row['orders']),
        'cancelled': _i(row['cancelled']),
        'revenue': round(_f(row['revenue']), 2),
        'profit': round(_f(row['profit']), 2),
        'unique_customers': _i(row['customers']),
    })