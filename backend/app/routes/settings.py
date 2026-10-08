"""
KitchenIQ — Settings Routes
GET  /api/settings/profile
PUT  /api/settings/profile
PUT  /api/settings/kitchen
PUT  /api/settings/password
GET  /api/settings/stats
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_one, execute_query
from app.utils.auth import token_required


settings_bp = Blueprint('settings', __name__)


def get_kitchen_id(user_id):
    k = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (user_id,),
    )
    return k['id'] if k else None


# ============================================================
# PROFILE
# ============================================================

@settings_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    user = execute_one(
        "SELECT id, email, full_name, role, created_at FROM users WHERE id = %s",
        (request.user_id,),
    )
    kitchen = execute_one(
        "SELECT id, name, city, address, phone FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (request.user_id,),
    )

    return jsonify({
        'user': {
            'id': user['id'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role'],
            'created_at': str(user['created_at']),
        },
        'kitchen': {
            'id': kitchen['id'],
            'name': kitchen['name'],
            'city': kitchen['city'],
            'address': kitchen['address'],
            'phone': kitchen['phone'],
        } if kitchen else None,
    })


@settings_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    d = request.get_json() or {}

    full_name = (d.get('full_name') or '').strip()
    if not full_name:
        return jsonify({'error': 'Full name is required'}), 400

    execute_query(
        "UPDATE users SET full_name = %s, updated_at = NOW() WHERE id = %s",
        (full_name, request.user_id),
        fetch=False,
    )

    return jsonify({'message': 'Profile updated'})


# ============================================================
# KITCHEN
# ============================================================

@settings_bp.route('/kitchen', methods=['PUT'])
@token_required
def update_kitchen():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    d = request.get_json() or {}

    execute_query(
        """
        UPDATE kitchens
        SET name = COALESCE(NULLIF(%s, ''), name),
            city = %s,
            address = %s,
            phone = %s,
            updated_at = NOW()
        WHERE id = %s AND user_id = %s
        """,
        (
            d.get('name', ''),
            d.get('city'),
            d.get('address'),
            d.get('phone'),
            kitchen_id,
            request.user_id,
        ),
        fetch=False,
    )

    return jsonify({'message': 'Kitchen updated'})


# ============================================================
# PASSWORD
# ============================================================

@settings_bp.route('/password', methods=['PUT'])
@token_required
def change_password():
    from werkzeug.security import check_password_hash, generate_password_hash

    d = request.get_json() or {}
    current = d.get('current_password') or ''
    new_pass = d.get('new_password') or ''

    if not current or not new_pass:
        return jsonify({'error': 'Both current and new passwords required'}), 400

    if len(new_pass) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400

    user = execute_one(
        "SELECT password_hash FROM users WHERE id = %s",
        (request.user_id,),
    )

    if not check_password_hash(user['password_hash'], current):
        return jsonify({'error': 'Current password is incorrect'}), 401

    new_hash = generate_password_hash(new_pass)

    execute_query(
        "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
        (new_hash, request.user_id),
        fetch=False,
    )

    return jsonify({'message': 'Password changed successfully'})


# ============================================================
# STATS
# ============================================================

@settings_bp.route('/stats', methods=['GET'])
@token_required
def stats():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    orders = execute_one(
        "SELECT COUNT(*)::int AS c FROM orders WHERE kitchen_id = %s",
        (kitchen_id,),
    )
    dishes = execute_one(
        "SELECT COUNT(DISTINCT item_name)::int AS c FROM order_items oi JOIN orders o ON o.id = oi.order_id WHERE o.kitchen_id = %s",
        (kitchen_id,),
    )
    customers = execute_one(
        "SELECT COUNT(DISTINCT customer_phone)::int AS c FROM orders WHERE kitchen_id = %s AND customer_phone IS NOT NULL",
        (kitchen_id,),
    )

    return jsonify({
        'total_orders': orders['c'] if orders else 0,
        'total_dishes': dishes['c'] if dishes else 0,
        'total_customers': customers['c'] if customers else 0,
    })