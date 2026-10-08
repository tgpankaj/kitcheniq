"""
KitchenIQ — Auth Routes
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import jwt
import re

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.services import audit_service
from app.services import email_service


auth_bp = Blueprint('auth', __name__)


# ============================================================
# HELPERS
# ============================================================

def is_valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email or ''))


def make_token(user_id, email):
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


# ============================================================
# SIGNUP
# POST /api/auth/register
# ============================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    full_name = (data.get('full_name') or '').strip()

    # Validate
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email address'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Check existing
    existing = execute_one('SELECT id FROM users WHERE email = %s', (email,))
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    # Hash password
    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash(password)

    # Insert user
    row = execute_one(
        """
        INSERT INTO users (email, password_hash, full_name, role)
        VALUES (%s, %s, %s, 'owner')
        RETURNING id, email, full_name, role, created_at
        """,
        (email, password_hash, full_name),
    )

    # Create a default kitchen for the user (so dashboard works immediately)
    kitchen = execute_one(
        """
        INSERT INTO kitchens (user_id, name, city)
        VALUES (%s, %s, %s)
        RETURNING id, name
        """,
        (row['id'], f"{full_name or email}'s Kitchen", ''),
    )

    # Add owner to kitchen_users
    execute_query(
        """
        INSERT INTO kitchen_users (kitchen_id, user_id, role, accepted_at)
        VALUES (%s, %s, 'owner', NOW())
        """,
        (kitchen['id'], row['id']),
        fetch=False,
    )

    # Audit log
    try:
        audit_service.log_signup(row['id'], kitchen['id'], email)
    except Exception:
        pass

    # Send welcome email (async-ish)
    try:
        email_service.send_welcome_email(row['id'], email, full_name)
    except Exception as e:
        print(f"[signup] welcome email failed: {e}")

    token = make_token(row['id'], row['email'])

    return jsonify({
        'message': 'Account created successfully',
        'token': token,
        'user': {
            'id': row['id'],
            'email': row['email'],
            'full_name': row['full_name'],
            'role': row['role'],
        },
        'kitchen': {
            'id': kitchen['id'],
            'name': kitchen['name'],
        },
    }), 201


# ============================================================
# LOGIN
# POST /api/auth/login
# ============================================================

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = execute_one(
        """
        SELECT id, email, password_hash, full_name, role
        FROM users
        WHERE email = %s
        """,
        (email,),
    )

    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Verify password
    from werkzeug.security import check_password_hash
    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Get first kitchen
    kitchen = execute_one(
        """
        SELECT id, name
        FROM kitchens
        WHERE user_id = %s
        ORDER BY id
        LIMIT 1
        """,
        (user['id'],),
    )

    # Audit log
    try:
        audit_service.log_login(user['id'], kitchen['id'] if kitchen else None, success=True)
    except Exception:
        pass

    token = make_token(user['id'], user['email'])

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role'],
        },
        'kitchen': {
            'id': kitchen['id'],
            'name': kitchen['name'],
        } if kitchen else None,
    })


# ============================================================
# ME (Protected — verify token works)
# GET /api/auth/me
# ============================================================

@auth_bp.route('/me', methods=['GET'])
@token_required
def me():
    user = execute_one(
        'SELECT id, email, full_name, role, created_at FROM users WHERE id = %s',
        (request.user_id,),
    )
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user['id'],
        'email': user['email'],
        'full_name': user['full_name'],
        'role': user['role'],
        'created_at': str(user['created_at']),
    })