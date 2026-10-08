"""
KitchenIQ — Public Routes (no auth required)
GET /api/public/stats        marketing stats
GET /api/public/plans        public plan list
"""
from flask import Blueprint, jsonify

from db.connection import execute_one


public_bp = Blueprint('public', __name__)


def _i(v):
    try:
        return int(v or 0)
    except (ValueError, TypeError):
        return 0


@public_bp.route('/stats', methods=['GET'])
def stats():
    """Return aggregated stats for landing page (no auth)."""

    # Count users/kitchens/orders (aggregate only)
    row = execute_one(
        """
        SELECT
            (SELECT COUNT(*)::int FROM users) AS users,
            (SELECT COUNT(*)::int FROM kitchens WHERE is_active = TRUE) AS kitchens,
            (SELECT COUNT(*)::int FROM orders) AS orders,
            (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status != 'cancelled') AS total_revenue
        """
    )

    return jsonify({
        'active_kitchens': _i(row['kitchens']) if row else 0,
        'total_users': _i(row['users']) if row else 0,
        'total_orders': _i(row['orders']) if row else 0,
        'total_revenue_processed': float(row['total_revenue']) if row else 0,
    })


@public_bp.route('/plans', methods=['GET'])
def plans():
    """Return public plan list (mirror of /api/plans/)."""
    from app.routes.plans import PLANS
    return jsonify(PLANS)
