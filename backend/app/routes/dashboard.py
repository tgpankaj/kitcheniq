"""
KitchenIQ — Dashboard Routes
GET /api/dashboard/summary
GET /api/dashboard/recent-orders
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_one
from app.utils.auth import token_required
from app.services.analytics_service import get_dashboard_summary, get_recent_orders


dashboard_bp = Blueprint('dashboard', __name__)


def get_kitchen_id(user_id):
    from app.utils.kitchen_context import get_current_kitchen_id
    return get_current_kitchen_id(user_id)


@dashboard_bp.route('/summary', methods=['GET'])
@token_required
def summary():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 7))
        if days not in (7, 30, 90):
            days = 7
    except (ValueError, TypeError):
        days = 7

    return jsonify(get_dashboard_summary(kitchen_id, days))


@dashboard_bp.route('/recent-orders', methods=['GET'])
@token_required
def recent():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    limit = min(int(request.args.get('limit', 10)), 50)
    return jsonify(get_recent_orders(kitchen_id, limit))