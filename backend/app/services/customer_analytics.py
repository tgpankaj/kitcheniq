"""
KitchenIQ — Customer Analytics Service (Advanced)
Cohorts, CLV, Churn Risk
"""
from db.connection import execute_query, execute_one


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
# COHORT ANALYSIS
# ============================================================
# Group customers by their first-order month, then track how many
# return each subsequent month.

def get_cohort_analysis(kitchen_id, months_back=6):
    """Return monthly cohort retention matrix."""

    rows = execute_query(
        """
        WITH first_orders AS (
            SELECT
                customer_phone,
                DATE_TRUNC('month', MIN(order_date))::date AS cohort_month
            FROM orders
            WHERE kitchen_id = %s
              AND customer_phone IS NOT NULL
              AND status != 'cancelled'
            GROUP BY customer_phone
        ),
        activity AS (
            SELECT DISTINCT
                o.customer_phone,
                DATE_TRUNC('month', o.order_date)::date AS order_month
            FROM orders o
            WHERE o.kitchen_id = %s
              AND o.customer_phone IS NOT NULL
              AND o.status != 'cancelled'
        )
        SELECT
            f.cohort_month::text AS cohort,
            a.order_month::text AS order_month,
            COUNT(DISTINCT a.customer_phone)::int AS customers
        FROM first_orders f
        JOIN activity a ON a.customer_phone = f.customer_phone
        WHERE f.cohort_month >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '%s months'
        GROUP BY f.cohort_month, a.order_month
        ORDER BY f.cohort_month, a.order_month
        """,
        (kitchen_id, kitchen_id, months_back),
    )

    if not rows:
        return {'cohorts': [], 'matrix': []}

    # Get unique cohort months (sorted)
    cohort_months = sorted(set(r['cohort'] for r in rows))

    # Build matrix: cohort -> { month_offset -> count }
    matrix = {}
    cohort_totals = {}

    for r in rows:
        c = r['cohort']
        m = r['order_month']
        cnt = r['customers']

        if c not in matrix:
            matrix[c] = {}

        # Calculate month offset
        c_year, c_month = map(int, c[:7].split('-'))
        m_year, m_month = map(int, m[:7].split('-'))
        offset = (m_year - c_year) * 12 + (m_month - c_month)

        matrix[c][offset] = cnt

        # Total customers in this cohort (offset 0)
        if offset == 0:
            cohort_totals[c] = cnt

    # Build output array
    result = []
    for c in cohort_months:
        total = cohort_totals.get(c, 0)
        if total == 0:
            continue

        # Get max offset needed
        retention = []
        max_offset = max(matrix[c].keys()) if matrix[c] else 0
        for offset in range(0, min(max_offset + 1, 12)):
            cnt = matrix[c].get(offset, 0)
            pct = round(cnt / total * 100, 1) if total > 0 else 0
            retention.append({'offset': offset, 'count': cnt, 'pct': pct})

        result.append({
            'cohort': c,
            'total_customers': total,
            'retention': retention,
        })

    return {'cohorts': result}


# ============================================================
# CUSTOMER LIFETIME VALUE
# ============================================================

def get_clv_summary(kitchen_id):
    """Return CLV stats, average order value, purchase frequency."""

    overall = execute_one(
        """
        SELECT
            COUNT(DISTINCT customer_phone)::int AS total_customers,
            COUNT(*) FILTER (WHERE customer_phone IS NOT NULL)::int AS total_orders,
            COALESCE(SUM(total_amount), 0) AS total_revenue
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone IS NOT NULL
          AND status != 'cancelled'
        """,
        (kitchen_id,),
    )

    total_customers = _i(overall['total_customers'])
    total_orders = _i(overall['total_orders'])
    total_revenue = _f(overall['total_revenue'])

    avg_orders_per_customer = total_orders / max(total_customers, 1)
    avg_order_value = total_revenue / max(total_orders, 1)
    avg_clv = total_revenue / max(total_customers, 1)

    # Top customers
    top = execute_query(
        """
        SELECT
            customer_phone AS phone,
            COALESCE(MAX(customer_name), '') AS name,
            COUNT(*)::int AS orders,
            COALESCE(SUM(total_amount), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone IS NOT NULL
          AND status != 'cancelled'
        GROUP BY customer_phone
        ORDER BY revenue DESC
        LIMIT 10
        """,
        (kitchen_id,),
    )

    return {
        'total_customers': total_customers,
        'avg_order_value': round(avg_order_value, 2),
        'avg_orders_per_customer': round(avg_orders_per_customer, 1),
        'avg_lifetime_value': round(avg_clv, 2),
        'top_customers': [
            {
                'phone': r['phone'],
                'name': r['name'] or r['phone'],
                'orders': _i(r['orders']),
                'revenue': round(_f(r['revenue']), 2),
                'clv_rank': i + 1,
            }
            for i, r in enumerate(top)
        ],
    }


# ============================================================
# CHURN RISK
# ============================================================

def get_churn_risk(kitchen_id):
    """Customers who ordered before but haven't in last 30 days."""
    rows = execute_query(
        """
        SELECT
            customer_phone AS phone,
            COALESCE(MAX(customer_name), '') AS name,
            COUNT(*)::int AS total_orders,
            COALESCE(SUM(total_amount), 0) AS total_spent,
            MIN(order_date)::text AS first_order,
            MAX(order_date)::text AS last_order,
            (CURRENT_DATE - MAX(order_date))::int AS days_since
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone IS NOT NULL
          AND status != 'cancelled'
        GROUP BY customer_phone
        HAVING MAX(order_date) < CURRENT_DATE - INTERVAL '30 days'
        ORDER BY total_spent DESC
        LIMIT 30
        """,
        (kitchen_id,),
    )

    return [
        {
            'phone': r['phone'],
            'name': r['name'] or r['phone'],
            'total_orders': _i(r['total_orders']),
            'total_spent': round(_f(r['total_spent']), 2),
            'first_order': r['first_order'],
            'last_order': r['last_order'],
            'days_since': _i(r['days_since']),
            'risk_level': 'high' if _i(r['days_since']) > 60 else 'medium',
        }
        for r in rows
    ]


# ============================================================
# SEGMENT REVENUE SHARE
# ============================================================

def get_segment_revenue_share(kitchen_id):
    """Revenue and customer count by RFM segment."""

    rows = execute_query(
        """
        WITH customer_stats AS (
            SELECT
                customer_phone,
                COUNT(*) AS freq,
                COALESCE(SUM(total_amount), 0) AS total,
                (CURRENT_DATE - MAX(order_date)) AS recency
            FROM orders
            WHERE kitchen_id = %s
              AND customer_phone IS NOT NULL
              AND status != 'cancelled'
            GROUP BY customer_phone
        )
        SELECT
            CASE
                WHEN recency <= 15 AND freq >= 5 AND total >= 3000 THEN 'VIP'
                WHEN recency <= 30 AND freq >= 3 THEN 'Loyal'
                WHEN recency <= 30 AND freq <= 2 THEN 'New'
                WHEN recency > 30 AND freq >= 3 THEN 'At Risk'
                ELSE 'Lost'
            END AS segment,
            COUNT(*)::int AS customers,
            COALESCE(SUM(total), 0) AS revenue,
            COALESCE(AVG(total), 0) AS avg_spent
        FROM customer_stats
        GROUP BY segment
        ORDER BY revenue DESC
        """,
        (kitchen_id,),
    )

    total_revenue = sum(_f(r['revenue']) for r in rows)

    return [
        {
            'segment': r['segment'],
            'customers': _i(r['customers']),
            'revenue': round(_f(r['revenue']), 2),
            'revenue_share_pct': round(_f(r['revenue']) / max(total_revenue, 1) * 100, 1),
            'avg_spent': round(_f(r['avg_spent']), 2),
        }
        for r in rows
    ]
