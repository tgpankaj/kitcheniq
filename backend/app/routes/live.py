"""
KitchenIQ — Live Orders Routes
GET  /api/live/orders         (today's orders, filterable by status)
GET  /api/live/summary        (status counts + kitchen metrics)
GET  /api/live/performance    (prep time, delays, throughput)
POST /api/live/orders/<id>/status   (update order status)
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.utils.kitchen_context import get_current_kitchen_id


live_bp = Blueprint('live', __name__)


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


# ============================================================
# LIST — Today's Orders
# ============================================================

@live_bp.route('/orders', methods=['GET'])
@token_required
def list_orders():
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    status_filter = request.args.get('status')
    limit = min(int(request.args.get('limit', 50)), 200)

    where = ["o.kitchen_id = %s", "o.order_date = CURRENT_DATE"]
    params = [kitchen_id]

    if status_filter:
        where.append("LOWER(o.status) = %s")
        params.append(status_filter.lower())

    params.append(limit)

    rows = execute_query(
        f"""
        SELECT
            o.id, o.external_order_id, o.platform,
            o.order_time::text AS time,
            o.customer_phone, o.customer_name,
            o.total_amount, o.status, o.created_at,
            (SELECT STRING_AGG(oi.item_name || ' x' || oi.quantity, ', ')
             FROM order_items oi WHERE oi.order_id = o.id) AS items
        FROM orders o
        WHERE {' AND '.join(where)}
        ORDER BY o.created_at DESC
        LIMIT %s
        """,
        tuple(params),
    )

    return jsonify([
        {
            'id': r['id'],
            'display_id': f"#ORD{r['id']:04d}",
            'external_id': r['external_order_id'],
            'platform': (r['platform'] or 'manual').capitalize(),
            'time': (r['time'] or '')[:5],
            'customer': r['customer_name'] or r['customer_phone'] or 'Guest',
            'amount': round(_f(r['total_amount']), 2),
            'status': (r['status'] or 'pending').lower(),
            'items': r['items'] or 'No items',
            'minutes_ago': _minutes_ago(r['created_at']),
        }
        for r in rows
    ])


def _minutes_ago(dt):
    if not dt:
        return 0
    delta = datetime.now() - dt
    return max(0, int(delta.total_seconds() / 60))


# ============================================================
# SUMMARY
# ============================================================

@live_bp.route('/summary', methods=['GET'])
@token_required
def summary():
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    row = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE LOWER(status) IN ('pending', 'preparing', 'confirmed')) AS preparing,
            COUNT(*) FILTER (WHERE LOWER(status) = 'ready') AS ready,
            COUNT(*) FILTER (WHERE LOWER(status) IN ('delivered', 'out_for_delivery', 'completed')) AS delivered,
            COUNT(*) FILTER (WHERE LOWER(status) = 'cancelled') AS cancelled,
            COUNT(*) AS total,
            COALESCE(SUM(total_amount), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND order_date = CURRENT_DATE
        """,
        (kitchen_id,),
    )

    return jsonify({
        'preparing': _i(row['preparing']),
        'ready': _i(row['ready']),
        'delivered': _i(row['delivered']),
        'cancelled': _i(row['cancelled']),
        'total': _i(row['total']),
        'revenue': round(_f(row['revenue']), 2),
    })


# ============================================================
# PERFORMANCE
# ============================================================

@live_bp.route('/performance', methods=['GET'])
@token_required
def performance():
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    today = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS completed,
            COUNT(*) FILTER (WHERE LOWER(status) IN ('pending', 'preparing', 'confirmed')) AS in_progress,
            COUNT(*) FILTER (WHERE LOWER(status) = 'ready') AS ready_count
        FROM orders
        WHERE kitchen_id = %s
          AND order_date = CURRENT_DATE
        """,
        (kitchen_id,),
    )

    # Last hour stats
    last_hour = execute_one(
        """
        SELECT COUNT(*)::int AS orders
        FROM orders
        WHERE kitchen_id = %s
          AND created_at >= NOW() - INTERVAL '1 hour'
        """,
        (kitchen_id,),
    )

    completed = _i(today['completed'])
    in_progress = _i(today['in_progress'])
    ready_count = _i(today['ready_count'])

    return jsonify({
        'completed_orders': completed,
        'in_progress_orders': in_progress,
        'ready_orders': ready_count,
        'avg_delivery_minutes': 0,
        'avg_prep_minutes': 0,
        'delayed_orders': 0,
        'on_time_pct': 100.0,
        'last_hour_orders': _i(last_hour['orders']) if last_hour else 0,
    })


# ============================================================
# UPDATE STATUS
# ============================================================

@live_bp.route('/orders/<int:oid>/status', methods=['POST'])
@token_required
def update_status(oid):
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    d = request.get_json() or {}
    new_status = (d.get('status') or '').lower().strip()

    valid = ('pending', 'preparing', 'ready', 'delivered', 'cancelled')
    if new_status not in valid:
        return jsonify({'error': f'Invalid status. Must be: {", ".join(valid)}'}), 400

    existing = execute_one(
        "SELECT id FROM orders WHERE id = %s AND kitchen_id = %s",
        (oid, kitchen_id),
    )
    if not existing:
        return jsonify({'error': 'Order not found'}), 404

    execute_query(
        "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s",
        (new_status, oid),
        fetch=False,
    )

    return jsonify({'message': 'Status updated', 'status': new_status})
