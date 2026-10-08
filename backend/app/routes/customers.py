"""
KitchenIQ — Customers Routes
GET /api/customers          (list with segments)
GET /api/customers/summary  (RFM + KPIs)
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.services import customer_analytics


customers_bp = Blueprint('customers', __name__)


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


def classify_segment(recency_days, frequency, monetary):
    """Simple RFM-based segment classifier."""
    if recency_days <= 15 and frequency >= 5 and monetary >= 3000:
        return 'VIP'
    if recency_days <= 30 and frequency >= 3:
        return 'Loyal'
    if recency_days <= 30 and frequency <= 2:
        return 'New'
    if recency_days > 30 and frequency >= 3:
        return 'At Risk'
    return 'Lost'


# ============================================================
# SUMMARY (KPIs + segment breakdown)
# ============================================================

@customers_bp.route('/summary', methods=['GET'])
@token_required
def summary():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 90))
        if days not in (30, 90, 180, 365):
            days = 90
    except (ValueError, TypeError):
        days = 90

    # Build customer aggregates from orders (fresh each time)
    rows = execute_query(
        """
        SELECT
            customer_phone AS phone,
            COALESCE(MAX(customer_name), '') AS name,
            COUNT(*) AS frequency,
            COALESCE(SUM(total_amount), 0) AS monetary,
            MIN(order_date) AS first_order,
            MAX(order_date) AS last_order,
            (CURRENT_DATE - MAX(order_date)) AS recency
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone IS NOT NULL
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY customer_phone
        """,
        (kitchen_id, days),
    )

    # Classify segments
    seg_counts = {'VIP': 0, 'Loyal': 0, 'New': 0, 'At Risk': 0, 'Lost': 0}
    total_spend = 0
    repeat_count = 0

    for r in rows:
        seg = classify_segment(_i(r['recency']), _i(r['frequency']), _f(r['monetary']))
        seg_counts[seg] += 1
        total_spend += _f(r['monetary'])
        if _i(r['frequency']) >= 2:
            repeat_count += 1

    total_customers = len(rows)
    repeat_rate = (repeat_count / max(total_customers, 1) * 100) if total_customers else 0
    avg_spend = total_spend / max(total_customers, 1)
    avg_orders = sum(_i(r['frequency']) for r in rows) / max(total_customers, 1)

    return jsonify({
        'period_days': days,
        'kpis': {
            'total_customers': total_customers,
            'repeat_customers': repeat_count,
            'repeat_rate_pct': round(repeat_rate, 1),
            'avg_order_value': round(avg_spend / max(avg_orders, 1), 2),
            'avg_lifetime_value': round(avg_spend, 2),
            'avg_orders_per_customer': round(avg_orders, 1),
        },
        'segments': [
            {'name': 'VIP',      'count': seg_counts['VIP']},
            {'name': 'Loyal',    'count': seg_counts['Loyal']},
            {'name': 'New',      'count': seg_counts['New']},
            {'name': 'At Risk',  'count': seg_counts['At Risk']},
            {'name': 'Lost',     'count': seg_counts['Lost']},
        ],
    })


# ============================================================
# LIST
# ============================================================

@customers_bp.route('/', methods=['GET'])
@token_required
def list_customers():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 90))
        if days not in (30, 90, 180, 365):
            days = 90
    except (ValueError, TypeError):
        days = 90

    limit = min(int(request.args.get('limit', 50)), 500)
    segment_filter = request.args.get('segment')  # optional

    rows = execute_query(
        """
        SELECT
            customer_phone AS phone,
            COALESCE(MAX(customer_name), '') AS name,
            COUNT(*) AS frequency,
            COALESCE(SUM(total_amount), 0) AS monetary,
            MIN(order_date) AS first_order,
            MAX(order_date) AS last_order,
            (CURRENT_DATE - MAX(order_date)) AS recency
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone IS NOT NULL
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY customer_phone
        ORDER BY monetary DESC
        LIMIT %s
        """,
        (kitchen_id, days, limit * 2),  # Fetch extra for filtering
    )

    result = []
    for r in rows:
        seg = classify_segment(_i(r['recency']), _i(r['frequency']), _f(r['monetary']))
        if segment_filter and seg.lower() != segment_filter.lower():
            continue

        result.append({
            'phone': r['phone'],
            'name': r['name'] or r['phone'],
            'orders': _i(r['frequency']),
            'total_spent': round(_f(r['monetary']), 2),
            'avg_order_value': round(_f(r['monetary']) / max(_i(r['frequency']), 1), 2),
            'first_order': str(r['first_order']) if r['first_order'] else None,
            'last_order': str(r['last_order']) if r['last_order'] else None,
            'recency_days': _i(r['recency']),
            'segment': seg,
        })

        if len(result) >= limit:
            break

    return jsonify(result)


# ============================================================
# TOP CUSTOMERS
# ============================================================

@customers_bp.route('/top', methods=['GET'])
@token_required
def top_customers():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    limit = min(int(request.args.get('limit', 10)), 50)

    rows = execute_query(
        """
        SELECT
            customer_phone AS phone,
            COALESCE(MAX(customer_name), '') AS name,
            COUNT(*) AS frequency,
            COALESCE(SUM(total_amount), 0) AS monetary
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone IS NOT NULL
          AND status != 'cancelled'
        GROUP BY customer_phone
        ORDER BY monetary DESC
        LIMIT %s
        """,
        (kitchen_id, limit),
    )

    return jsonify([
        {
            'name': r['name'] or r['phone'],
            'phone': r['phone'],
            'orders': _i(r['frequency']),
            'total_spent': round(_f(r['monetary']), 2),
        }
        for r in rows
    ])


# ============================================================
# COHORT ANALYSIS
# ============================================================

@customers_bp.route('/cohorts', methods=['GET'])
@token_required
def cohorts():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        months = int(request.args.get('months', 6))
        if months not in (3, 6, 12):
            months = 6
    except (ValueError, TypeError):
        months = 6

    return jsonify(customer_analytics.get_cohort_analysis(kitchen_id, months))


@customers_bp.route('/clv', methods=['GET'])
@token_required
def clv():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404
    return jsonify(customer_analytics.get_clv_summary(kitchen_id))


@customers_bp.route('/churn-risk', methods=['GET'])
@token_required
def churn_risk():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404
    return jsonify(customer_analytics.get_churn_risk(kitchen_id))


@customers_bp.route('/segment-revenue', methods=['GET'])
@token_required
def segment_revenue():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404
    return jsonify(customer_analytics.get_segment_revenue_share(kitchen_id))
