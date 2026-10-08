"""
KitchenIQ — Analytics Service
Dashboard KPI and chart calculations.
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


def get_dashboard_summary(kitchen_id, days=7):
    """Returns KPIs, trend data, platform breakdown."""

    # Current period KPIs
    kpis = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS total_orders,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue,
            COALESCE(SUM(net_revenue) FILTER (WHERE status != 'cancelled'), 0) AS net_revenue,
            COALESCE(SUM(profit) FILTER (WHERE status != 'cancelled'), 0) AS profit,
            COALESCE(AVG(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS aov,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COUNT(*) AS total_all
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days),
    )

    total_orders = _i(kpis['total_orders'])
    cancelled = _i(kpis['cancelled'])
    total_all = _i(kpis['total_all'])
    cancellation_rate = (cancelled / max(total_all, 1) * 100) if total_all else 0

    # Previous period for growth %
    prev = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
          AND order_date < CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days * 2, days),
    )

    def growth(curr, prev_val):
        curr, prev_val = _f(curr), _f(prev_val)
        if prev_val <= 0:
            return 0.0
        return round((curr - prev_val) / prev_val * 100, 1)

    # Trend (daily)
    trend_rows = execute_query(
        """
        SELECT
            order_date::text AS date,
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

    # Platform breakdown
    platform_rows = execute_query(
        """
        SELECT
            COALESCE(platform, 'Unknown') AS platform,
            COUNT(*) AS orders,
            COALESCE(SUM(total_amount), 0) AS gross,
            COALESCE(SUM(platform_fee), 0) AS commission,
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

    return {
        'period_days': days,
        'kpis': {
            'total_revenue': round(_f(kpis['revenue']), 2),
            'total_orders': total_orders,
            'net_profit': round(_f(kpis['profit']), 2),
            'net_revenue': round(_f(kpis['net_revenue']), 2),
            'avg_order_value': round(_f(kpis['aov']), 2),
            'cancellation_rate': round(cancellation_rate, 1),
            'revenue_growth_pct': growth(kpis['revenue'], prev['revenue'] if prev else 0),
            'orders_growth_pct': growth(kpis['total_orders'], prev['orders'] if prev else 0),
        },
        'trend': {
            'labels': [r['date'] for r in trend_rows],
            'revenue': [round(_f(r['revenue']), 2) for r in trend_rows],
            'profit': [round(_f(r['profit']), 2) for r in trend_rows],
        },
        'platforms': {
            'labels': [r['platform'].capitalize() for r in platform_rows],
            'gross_revenue': [round(_f(r['gross']), 2) for r in platform_rows],
            'commission': [round(_f(r['commission']), 2) for r in platform_rows],
            'profit': [round(_f(r['profit']), 2) for r in platform_rows],
        },
    }


def get_recent_orders(kitchen_id, limit=10):
    """Returns most recent orders."""
    rows = execute_query(
        """
        SELECT
            o.id, o.order_date::text AS date, o.order_time::text AS time,
            o.platform, o.customer_phone, o.customer_name,
            o.total_amount, o.status
        FROM orders o
        WHERE o.kitchen_id = %s
        ORDER BY o.id DESC
        LIMIT %s
        """,
        (kitchen_id, limit),
    )

    return [
        {
            'id': f"#ORD{r['id']:04d}",
            'date': r['date'],
            'time': (str(r['time'])[:5] if r['time'] else ''),
            'platform': r['platform'] or 'Manual',
            'customer': r['customer_name'] or r['customer_phone'] or 'Guest',
            'amount': round(_f(r['total_amount']), 2),
            'status': (r['status'] or 'pending').lower(),
        }
        for r in rows
    ]