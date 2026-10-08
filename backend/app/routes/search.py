"""
KitchenIQ — Global Search
GET /api/search/?q=chicken&limit=10
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required


search_bp = Blueprint('search', __name__)


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
    k = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (user_id,),
    )
    return k['id'] if k else None


@search_bp.route('/', methods=['GET'])
@token_required
def search():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify({'orders': [], 'customers': [], 'dishes': []})

    limit = min(int(request.args.get('limit', 5)), 20)
    pattern = f'%{q}%'

    # Orders — match by id, external_id, customer_phone, customer_name, platform
    orders = execute_query(
        """
        SELECT id, external_order_id, platform, order_date::text AS date,
               customer_phone, customer_name, total_amount, status
        FROM orders
        WHERE kitchen_id = %s
          AND (
            CAST(id AS TEXT) ILIKE %s OR
            external_order_id ILIKE %s OR
            customer_phone ILIKE %s OR
            customer_name ILIKE %s OR
            platform ILIKE %s
          )
        ORDER BY id DESC
        LIMIT %s
        """,
        (kitchen_id, pattern, pattern, pattern, pattern, pattern, limit),
    )

    # Customers — phone or name
    customers = execute_query(
        """
        SELECT
            customer_phone AS phone,
            COALESCE(MAX(customer_name), '') AS name,
            COUNT(*) AS orders,
            COALESCE(SUM(total_amount), 0) AS total_spent
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone IS NOT NULL
          AND status != 'cancelled'
          AND (customer_phone ILIKE %s OR customer_name ILIKE %s)
        GROUP BY customer_phone
        ORDER BY total_spent DESC
        LIMIT %s
        """,
        (kitchen_id, pattern, pattern, limit),
    )

    # Dishes — item_name
    dishes = execute_query(
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
          AND oi.item_name ILIKE %s
        GROUP BY oi.item_name
        ORDER BY revenue DESC
        LIMIT %s
        """,
        (kitchen_id, pattern, limit),
    )

    return jsonify({
        'query': q,
        'orders': [
            {
                'id': r['id'],
                'display_id': f"#ORD{r['id']:04d}",
                'external_id': r['external_order_id'],
                'platform': (r['platform'] or '').capitalize(),
                'date': r['date'],
                'customer': r['customer_name'] or r['customer_phone'] or 'Guest',
                'amount': round(_f(r['total_amount']), 2),
                'status': (r['status'] or '').lower(),
                'link': f"/pages/dashboard.html",
            }
            for r in orders
        ],
        'customers': [
            {
                'phone': r['phone'],
                'name': r['name'] or r['phone'],
                'orders': _i(r['orders']),
                'total_spent': round(_f(r['total_spent']), 2),
                'link': '/pages/customers.html',
            }
            for r in customers
        ],
        'dishes': [
            {
                'name': r['name'],
                'orders': _i(r['orders']),
                'qty': _i(r['qty']),
                'revenue': round(_f(r['revenue']), 2),
                'link': '/pages/dishes.html',
            }
            for r in dishes
        ],
    })


@search_bp.route('/quick', methods=['GET'])
@token_required
def quick():
    """Quick search — returns flat list of top 8 results."""
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify([])

    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])

    pattern = f'%{q}%'
    results = []

    # Top 4 dishes
    dishes = execute_query(
        """
        SELECT oi.item_name AS name, COUNT(*) AS cnt
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE o.kitchen_id = %s AND oi.item_name ILIKE %s
        GROUP BY oi.item_name
        LIMIT 4
        """,
        (kitchen_id, pattern),
    )
    for d in dishes:
        results.append({
            'type': 'dish',
            'icon': 'fa-burger',
            'label': d['name'],
            'sub': f"{_i(d['cnt'])} orders",
            'link': '/pages/dishes.html',
        })

    # Top 2 customers
    customers = execute_query(
        """
        SELECT customer_phone, MAX(customer_name) AS name, COUNT(*) AS cnt
        FROM orders
        WHERE kitchen_id = %s AND customer_phone IS NOT NULL
          AND (customer_phone ILIKE %s OR customer_name ILIKE %s)
        GROUP BY customer_phone
        LIMIT 2
        """,
        (kitchen_id, pattern, pattern),
    )
    for c in customers:
        results.append({
            'type': 'customer',
            'icon': 'fa-user',
            'label': c['name'] or c['customer_phone'],
            'sub': c['customer_phone'],
            'link': '/pages/customers.html',
        })

    # Top 2 orders
    orders = execute_query(
        """
        SELECT id, platform, total_amount
        FROM orders
        WHERE kitchen_id = %s
          AND (CAST(id AS TEXT) ILIKE %s OR external_order_id ILIKE %s OR customer_phone ILIKE %s)
        ORDER BY id DESC
        LIMIT 2
        """,
        (kitchen_id, pattern, pattern, pattern),
    )
    for o in orders:
        results.append({
            'type': 'order',
            'icon': 'fa-receipt',
            'label': f"#ORD{o['id']:04d}",
            'sub': f"{(o['platform'] or '').capitalize()} · ₹{_f(o['total_amount']):.0f}",
            'link': '/pages/dashboard.html',
        })

    return jsonify(results[:8])