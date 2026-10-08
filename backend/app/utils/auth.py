"""
KitchenIQ — Auth Middleware
JWT verification decorator for protected routes.
"""
from functools import wraps
from flask import request, jsonify, current_app
import jwt


def token_required(f):
    """Decorator: requires valid JWT in Authorization header."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '').strip()

        if not token:
            return jsonify({'error': 'Authentication token missing'}), 401

        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256'],
            )
            request.user_id = data['user_id']
            request.user_email = data.get('email', '')

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired. Please login again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated