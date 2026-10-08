"""
KitchenIQ — Team Routes
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash

from db.connection import execute_one, execute_query
from app.utils.auth import token_required
from app.services import audit_service


team_bp = Blueprint('team', __name__)

VALID_ROLES = ('owner', 'manager', 'staff', 'analyst')


def get_kitchen_id(user_id):
    k = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (user_id,),
    )
    return k['id'] if k else None


def get_current_role(user_id, kitchen_id):
    row = execute_one(
        "SELECT role FROM kitchen_users WHERE user_id = %s AND kitchen_id = %s AND is_active = TRUE",
        (user_id, kitchen_id),
    )
    if row:
        return row['role']
    owner = execute_one("SELECT user_id FROM kitchens WHERE id = %s", (kitchen_id,))
    if owner and owner['user_id'] == user_id:
        return 'owner'
    return None


def require_role(user_id, kitchen_id, allowed):
    return get_current_role(user_id, kitchen_id) in allowed


@team_bp.route('/', methods=['GET'])
@token_required
def list_members():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    rows = execute_query(
        """
        SELECT ku.id AS membership_id, ku.role, ku.invited_at, ku.accepted_at,
               u.id AS user_id, u.email, u.full_name
        FROM kitchen_users ku
        JOIN users u ON u.id = ku.user_id
        WHERE ku.kitchen_id = %s AND ku.is_active = TRUE
        ORDER BY CASE ku.role
                 WHEN 'owner' THEN 1 WHEN 'manager' THEN 2
                 WHEN 'analyst' THEN 3 WHEN 'staff' THEN 4 ELSE 5 END
        """,
        (kitchen_id,),
    )

    return jsonify([
        {
            'id': r['membership_id'],
            'user_id': r['user_id'],
            'email': r['email'],
            'full_name': r['full_name'] or r['email'].split('@')[0],
            'role': r['role'],
            'is_current_user': r['user_id'] == request.user_id,
        }
        for r in rows
    ])


@team_bp.route('/invite', methods=['POST'])
@token_required
def invite():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    if not require_role(request.user_id, kitchen_id, ('owner', 'manager')):
        return jsonify({'error': 'Only owner or manager can invite'}), 403

    d = request.get_json() or {}
    email = (d.get('email') or '').strip().lower()
    full_name = (d.get('full_name') or '').strip()
    password = d.get('password') or ''
    role = (d.get('role') or 'staff').lower()

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    if role not in VALID_ROLES or role == 'owner':
        return jsonify({'error': 'Invalid role'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be 6+ characters'}), 400

    existing_user = execute_one("SELECT id FROM users WHERE email = %s", (email,))

    if existing_user:
        user_id = existing_user['id']
    else:
        row = execute_one(
            "INSERT INTO users (email, password_hash, full_name, role) VALUES (%s, %s, %s, %s) RETURNING id",
            (email, generate_password_hash(password), full_name, role),
        )
        user_id = row['id']

    existing = execute_one(
        "SELECT id, is_active FROM kitchen_users WHERE kitchen_id = %s AND user_id = %s",
        (kitchen_id, user_id),
    )

    if existing and existing['is_active']:
        return jsonify({'error': 'Already a team member'}), 409

    if existing:
        execute_query(
            "UPDATE kitchen_users SET role = %s, is_active = TRUE, accepted_at = NOW() WHERE id = %s",
            (role, existing['id']), fetch=False,
        )
        mid = existing['id']
    else:
        row = execute_one(
            "INSERT INTO kitchen_users (kitchen_id, user_id, role, accepted_at) VALUES (%s, %s, %s, NOW()) RETURNING id",
            (kitchen_id, user_id, role),
        )
        mid = row['id']

    return jsonify({
        'message': f'{role.capitalize()} added',
        'membership_id': mid,
        'email': email,
        'role': role,
    }), 201


@team_bp.route('/<int:mid>', methods=['PUT'])
@token_required
def update_role(mid):
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    if not require_role(request.user_id, kitchen_id, ('owner',)):
        return jsonify({'error': 'Only owner can change roles'}), 403

    d = request.get_json() or {}
    new_role = (d.get('role') or '').lower()

    if new_role not in VALID_ROLES or new_role == 'owner':
        return jsonify({'error': 'Invalid role'}), 400

    m = execute_one(
        "SELECT user_id FROM kitchen_users WHERE id = %s AND kitchen_id = %s AND is_active = TRUE",
        (mid, kitchen_id),
    )
    if not m:
        return jsonify({'error': 'Member not found'}), 404

    if m['user_id'] == request.user_id:
        return jsonify({'error': 'Cannot change your own role'}), 400

    execute_query("UPDATE kitchen_users SET role = %s WHERE id = %s", (new_role, mid), fetch=False)
    return jsonify({'message': 'Role updated', 'role': new_role})


@team_bp.route('/<int:mid>', methods=['DELETE'])
@token_required
def remove_member(mid):
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    if not require_role(request.user_id, kitchen_id, ('owner', 'manager')):
        return jsonify({'error': 'Permission denied'}), 403

    m = execute_one(
        "SELECT user_id, role FROM kitchen_users WHERE id = %s AND kitchen_id = %s",
        (mid, kitchen_id),
    )
    if not m:
        return jsonify({'error': 'Not found'}), 404

    if m['user_id'] == request.user_id or m['role'] == 'owner':
        return jsonify({'error': 'Cannot remove this member'}), 400

    execute_query("UPDATE kitchen_users SET is_active = FALSE WHERE id = %s", (mid,), fetch=False)
    return jsonify({'message': 'Member removed'})


@team_bp.route('/me', methods=['GET'])
@token_required
def my_role():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    return jsonify({
        'kitchen_id': kitchen_id,
        'user_id': request.user_id,
        'role': get_current_role(request.user_id, kitchen_id) or 'none',
    })