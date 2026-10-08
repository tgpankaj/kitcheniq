"""
KitchenIQ — Finance Routes
GET /api/finance/pnl              (P&L statement)
GET /api/finance/cost-breakdown   (Cost structure)
GET /api/finance/platforms        (Platform-wise)
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required


finance_bp = Blueprint('finance', __name__)


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
# P&L STATEMENT
# ============================================================

@finance_bp.route('/pnl', methods=['GET'])
@token_required
def pnl():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)

    row = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS gross_revenue,
            COALESCE(SUM(discount) FILTER (WHERE status != 'cancelled'), 0) AS discounts,
            COALESCE(SUM(tax) FILTER (WHERE status != 'cancelled'), 0) AS tax,
            COALESCE(SUM(platform_fee) FILTER (WHERE status != 'cancelled'), 0) AS platform_fees,
            COALESCE(SUM(delivery_fee) FILTER (WHERE status != 'cancelled'), 0) AS delivery_fees,
            COALESCE(SUM(packaging_cost) FILTER (WHERE status != 'cancelled'), 0) AS packaging,
            COALESCE(SUM(food_cost) FILTER (WHERE status != 'cancelled'), 0) AS food_cost,
            COALESCE(SUM(net_revenue) FILTER (WHERE status != 'cancelled'), 0) AS net_revenue,
            COALESCE(SUM(profit) FILTER (WHERE status != 'cancelled'), 0) AS profit
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days),
    )

    gross = _f(row['gross_revenue'])
    discounts = _f(row['discounts'])
    platform_fees = _f(row['platform_fees'])
    packaging = _f(row['packaging'])
    food_cost = _f(row['food_cost'])
    net_revenue = _f(row['net_revenue'])
    profit = _f(row['profit'])

    # Compute derived
    net_sales = gross - discounts
    total_costs = food_cost + platform_fees + packaging
    margin_pct = (profit / gross * 100) if gross > 0 else 0

    return jsonify({
        'period_days': days,
        'orders': _i(row['orders']),

        # Revenue section
        'gross_revenue': round(gross, 2),
        'discounts': round(discounts, 2),
        'net_sales': round(net_sales, 2),

        # Cost section
        'food_cost': round(food_cost, 2),
        'platform_fees': round(platform_fees, 2),
        'packaging_cost': round(packaging, 2),
        'total_costs': round(total_costs, 2),

        # Bottom line
        'net_revenue': round(net_revenue, 2),
        'profit': round(profit, 2),
        'profit_margin_pct': round(margin_pct, 1),

        # Percentages
        'food_cost_pct': round(food_cost / gross * 100, 1) if gross else 0,
        'platform_fee_pct': round(platform_fees / gross * 100, 1) if gross else 0,
        'packaging_pct': round(packaging / gross * 100, 1) if gross else 0,
        'discount_pct': round(discounts / gross * 100, 1) if gross else 0,
    })


# ============================================================
# COST BREAKDOWN
# ============================================================

@finance_bp.route('/cost-breakdown', methods=['GET'])
@token_required
def cost_breakdown():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)

    row = execute_one(
        """
        SELECT
            COALESCE(SUM(food_cost), 0) AS food_cost,
            COALESCE(SUM(platform_fee), 0) AS platform_fees,
            COALESCE(SUM(packaging_cost), 0) AS packaging,
            COALESCE(SUM(delivery_fee), 0) AS delivery,
            COALESCE(SUM(discount), 0) AS discounts
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days),
    )

    return jsonify({
        'labels': ['Food Cost', 'Platform Fees', 'Packaging', 'Delivery', 'Discounts'],
        'values': [
            round(_f(row['food_cost']), 2),
            round(_f(row['platform_fees']), 2),
            round(_f(row['packaging']), 2),
            round(_f(row['delivery']), 2),
            round(_f(row['discounts']), 2),
        ],
    })


# ============================================================
# PLATFORM-WISE P&L
# ============================================================

@finance_bp.route('/platforms', methods=['GET'])
@token_required
def platforms():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)

    rows = execute_query(
        """
        SELECT
            COALESCE(platform, 'manual') AS platform,
            COUNT(*) AS orders,
            COALESCE(SUM(total_amount), 0) AS gross,
            COALESCE(SUM(discount), 0) AS discounts,
            COALESCE(SUM(platform_fee), 0) AS fees,
            COALESCE(SUM(food_cost), 0) AS food_cost,
            COALESCE(SUM(packaging_cost), 0) AS packaging,
            COALESCE(SUM(profit), 0) AS profit
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY platform
        ORDER BY gross DESC
        """,
        (kitchen_id, days),
    )

    return jsonify([
        {
            'platform': r['platform'].capitalize(),
            'orders': _i(r['orders']),
            'gross_revenue': round(_f(r['gross']), 2),
            'discounts': round(_f(r['discounts']), 2),
            'platform_fees': round(_f(r['fees']), 2),
            'food_cost': round(_f(r['food_cost']), 2),
            'packaging_cost': round(_f(r['packaging']), 2),
            'profit': round(_f(r['profit']), 2),
            'margin_pct': round(_f(r['profit']) / max(_f(r['gross']), 1) * 100, 1),
            'fee_pct': round(_f(r['fees']) / max(_f(r['gross']), 1) * 100, 1),
        }
        for r in rows
    ])