"""
KitchenIQ — Dishes Routes
GET /api/dishes/menu-engineering   (Star/Plowhorse/Puzzle/Dog)
GET /api/dishes/                    (list with metrics)
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required


dishes_bp = Blueprint('dishes', __name__)


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


def classify_menu_engineering(qty, margin_pct, avg_qty, avg_margin):
    """
    Classic menu engineering matrix:
    - Star:       High popularity, High profitability
    - Plowhorse:  High popularity, Low profitability
    - Puzzle:     Low popularity, High profitability
    - Dog:        Low popularity, Low profitability
    """
    high_pop = qty >= avg_qty
    high_profit = margin_pct >= avg_margin

    if high_pop and high_profit:
        return 'Star'
    if high_pop and not high_profit:
        return 'Plowhorse'
    if not high_pop and high_profit:
        return 'Puzzle'
    return 'Dog'


# ============================================================
# MENU ENGINEERING
# ============================================================

@dishes_bp.route('/menu-engineering', methods=['GET'])
@token_required
def menu_engineering():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 30))
        if days not in (7, 30, 90, 365):
            days = 30
    except (ValueError, TypeError):
        days = 30

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
        """,
        (kitchen_id, days),
    )

    if not rows:
        return jsonify({'dishes': [], 'summary': {}, 'matrix': {}})

    # Calculate metrics (food cost estimated as 40% of revenue for now)
    dishes = []
    for r in rows:
        revenue = _f(r['revenue'])
        qty = _i(r['qty'])
        est_cost = revenue * 0.4
        profit = revenue - est_cost
        margin = (profit / revenue * 100) if revenue > 0 else 0

        dishes.append({
            'name': r['name'],
            'orders': _i(r['orders']),
            'quantity': qty,
            'revenue': round(revenue, 2),
            'est_cost': round(est_cost, 2),
            'profit': round(profit, 2),
            'margin_pct': round(margin, 1),
        })

    # Averages for classification
    avg_qty = sum(d['quantity'] for d in dishes) / len(dishes)
    avg_margin = sum(d['margin_pct'] for d in dishes) / len(dishes)

    # Classify
    matrix = {'Star': [], 'Plowhorse': [], 'Puzzle': [], 'Dog': []}
    for d in dishes:
        d['classification'] = classify_menu_engineering(
            d['quantity'], d['margin_pct'], avg_qty, avg_margin
        )
        matrix[d['classification']].append(d)

    return jsonify({
        'period_days': days,
        'dishes': dishes,
        'summary': {
            'total_dishes': len(dishes),
            'stars': len(matrix['Star']),
            'plowhorses': len(matrix['Plowhorse']),
            'puzzles': len(matrix['Puzzle']),
            'dogs': len(matrix['Dog']),
            'avg_quantity': round(avg_qty, 1),
            'avg_margin_pct': round(avg_margin, 1),
        },
        'matrix': {
            'Star': [d['name'] for d in matrix['Star']],
            'Plowhorse': [d['name'] for d in matrix['Plowhorse']],
            'Puzzle': [d['name'] for d in matrix['Puzzle']],
            'Dog': [d['name'] for d in matrix['Dog']],
        },
    })


# ============================================================
# DISHES LIST
# ============================================================

@dishes_bp.route('/', methods=['GET'])
@token_required
def list_dishes():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 30))
        if days not in (7, 30, 90, 365):
            days = 30
    except (ValueError, TypeError):
        days = 30

    rows = execute_query(
        """
        SELECT
            oi.item_name AS name,
            COUNT(DISTINCT oi.order_id) AS orders,
            COALESCE(SUM(oi.quantity), 0) AS qty,
            COALESCE(SUM(oi.line_total), 0) AS revenue,
            COALESCE(AVG(oi.unit_price), 0) AS avg_price
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE o.kitchen_id = %s
          AND o.status != 'cancelled'
          AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY oi.item_name
        ORDER BY revenue DESC
        """,
        (kitchen_id, days),
    )

    return jsonify([
        {
            'name': r['name'],
            'orders': _i(r['orders']),
            'quantity': _i(r['qty']),
            'revenue': round(_f(r['revenue']), 2),
            'avg_price': round(_f(r['avg_price']), 2),
        }
        for r in rows
    ])