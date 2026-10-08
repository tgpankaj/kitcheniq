"""
KitchenIQ — Analytics Routes
GET /api/analytics/dishes       (dish performance)
GET /api/analytics/peak-hours   (hourly breakdown)
GET /api/analytics/cancellations
GET /api/analytics/trends
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required


analytics_bp = Blueprint('analytics', __name__)


def _f(v):
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def _i(v):
    try:
        return int(v or 0)
    except (ValueError, TypeError):
        return 0


def get_kitchen_id(user_id):
    from app.utils.kitchen_context import get_current_kitchen_id
    return get_current_kitchen_id(user_id)


def get_days(req, default=30):
    try:
        d = int(req.args.get('days', default))
        return d if d in (7, 30, 90, 365) else default
    except (ValueError, TypeError):
        return default


# ============================================================
# DISH PERFORMANCE
# ============================================================

@analytics_bp.route('/dishes', methods=['GET'])
@token_required
def dishes():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    limit = min(int(request.args.get('limit', 20)), 100)

    rows = execute_query(
        """
        SELECT
            oi.item_name AS name,
            COUNT(DISTINCT oi.order_id) AS orders,
            COALESCE(SUM(oi.quantity), 0) AS qty,
            COALESCE(SUM(oi.line_total), 0) AS revenue
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE o.kitchen_id = %s
          AND o.status != 'cancelled'
          AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY oi.item_name
        HAVING SUM(oi.quantity) > 0
        ORDER BY revenue DESC
        LIMIT %s
        """,
        (kitchen_id, days, limit),
    )

    # Estimate food cost as 40% of revenue (we'll get accurate cost from menu_items later)
    result = []
    for r in rows:
        revenue = _f(r['revenue'])
        est_food_cost = round(revenue * 0.4, 2)
        profit = revenue - est_food_cost
        margin = (profit / revenue * 100) if revenue > 0 else 0

        result.append({
            'name': r['name'],
            'orders': _i(r['orders']),
            'quantity': _i(r['qty']),
            'revenue': round(revenue, 2),
            'food_cost': est_food_cost,
            'profit': round(profit, 2),
            'margin_pct': round(margin, 1),
        })

    return jsonify(result)


# ============================================================
# PEAK HOURS
# ============================================================

@analytics_bp.route('/peak-hours', methods=['GET'])
@token_required
def peak_hours():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)

    rows = execute_query(
        """
        SELECT
            EXTRACT(HOUR FROM order_time)::int AS hour,
            COUNT(*) AS orders,
            COALESCE(SUM(total_amount), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND order_time IS NOT NULL
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY EXTRACT(HOUR FROM order_time)
        ORDER BY hour
        """,
        (kitchen_id, days),
    )

    # Fill all 24 hours
    hour_map = {r['hour']: r for r in rows}
    result = []
    for h in range(24):
        r = hour_map.get(h)
        result.append({
            'hour': h,
            'label': f"{h:02d}:00",
            'orders': _i(r['orders']) if r else 0,
            'revenue': round(_f(r['revenue']), 2) if r else 0,
        })

    return jsonify(result)


# ============================================================
# CANCELLATIONS
# ============================================================

@analytics_bp.route('/cancellations', methods=['GET'])
@token_required
def cancellations():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)

    # Overall
    overall = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COUNT(*) AS total,
            COALESCE(SUM(total_amount) FILTER (WHERE status = 'cancelled'), 0) AS lost_revenue
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days),
    )

    total = _i(overall['total'])
    cancelled = _i(overall['cancelled'])
    rate = (cancelled / max(total, 1) * 100) if total else 0

    # By platform
    by_platform = execute_query(
        """
        SELECT
            platform,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COUNT(*) AS total
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY platform
        ORDER BY total DESC
        """,
        (kitchen_id, days),
    )

    return jsonify({
        'overall': {
            'cancelled': cancelled,
            'total': total,
            'rate_pct': round(rate, 1),
            'lost_revenue': round(_f(overall['lost_revenue']), 2),
        },
        'by_platform': [
            {
                'platform': (r['platform'] or 'Unknown').capitalize(),
                'cancelled': _i(r['cancelled']),
                'total': _i(r['total']),
                'rate_pct': round(_i(r['cancelled']) / max(_i(r['total']), 1) * 100, 1),
            }
            for r in by_platform
        ],
    })


# ============================================================
# TRENDS (daily / weekly / monthly)
# ============================================================

@analytics_bp.route('/trends', methods=['GET'])
@token_required
def trends():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)

    # Daily
    daily = execute_query(
        """
        SELECT
            order_date::text AS date,
            COUNT(*) AS orders,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(profit), 0) AS profit
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY order_date
        ORDER BY order_date
        """,
        (kitchen_id, days),
    )

    return jsonify({
        'period_days': days,
        'daily': [
            {
                'date': r['date'],
                'orders': _i(r['orders']),
                'revenue': round(_f(r['revenue']), 2),
                'profit': round(_f(r['profit']), 2),
            }
            for r in daily
        ],
    })