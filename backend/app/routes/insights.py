"""
KitchenIQ — Insights Routes
GET /api/insights/           (all insights, filter by category)
GET /api/insights/summary    (counts by type)
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_one
from app.utils.auth import token_required
from app.services.insights_service import generate_insights


insights_bp = Blueprint('insights', __name__)


def get_kitchen_id(user_id):
    from app.utils.kitchen_context import get_current_kitchen_id
    return get_current_kitchen_id(user_id)


@insights_bp.route('/', methods=['GET'])
@token_required
def list_insights():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 30))
        if days not in (7, 30, 90, 365):
            days = 30
    except (ValueError, TypeError):
        days = 30

    category = request.args.get('category')  # menu, commission, revenue, operations, customers

    insights = generate_insights(kitchen_id, days)

    if category:
        insights = [i for i in insights if i['category'].lower() == category.lower()]

    return jsonify(insights)


@insights_bp.route('/summary', methods=['GET'])
@token_required
def summary():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 30))
        if days not in (7, 30, 90, 365):
            days = 30
    except (ValueError, TypeError):
        days = 30

    insights = generate_insights(kitchen_id, days)

    by_type = {'danger': 0, 'warning': 0, 'info': 0, 'success': 0}
    by_category = {}

    for i in insights:
        by_type[i['type']] = by_type.get(i['type'], 0) + 1
        cat = i['category']
        by_category[cat] = by_category.get(cat, 0) + 1

    return jsonify({
        'total': len(insights),
        'by_type': by_type,
        'by_category': by_category,
    })