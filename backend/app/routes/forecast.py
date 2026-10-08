"""
KitchenIQ — Forecast Routes
GET /api/forecast/orders      7/30-day order prediction
GET /api/forecast/hourly      hourly distribution
GET /api/forecast/items       top item demand
"""
from flask import Blueprint, request, jsonify

from app.utils.auth import token_required
from app.utils.kitchen_context import get_current_kitchen_id
from app.services import forecast_service


forecast_bp = Blueprint('forecast', __name__)


@forecast_bp.route('/orders', methods=['GET'])
@token_required
def orders_forecast():
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 7))
        if days not in (7, 14, 30):
            days = 7
    except (ValueError, TypeError):
        days = 7

    return jsonify(forecast_service.forecast(kitchen_id, days))


@forecast_bp.route('/hourly', methods=['GET'])
@token_required
def hourly():
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    return jsonify(forecast_service.hourly_forecast(kitchen_id))


@forecast_bp.route('/items', methods=['GET'])
@token_required
def items():
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 7))
    except (ValueError, TypeError):
        days = 7

    limit = min(int(request.args.get('limit', 10)), 50)

    return jsonify(forecast_service.items_forecast(kitchen_id, days, limit))
