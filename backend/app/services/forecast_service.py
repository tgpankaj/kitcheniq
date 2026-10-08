"""
KitchenIQ — Demand Forecasting Service
Predicts future orders/revenue using historical patterns.

Methods used:
- 7-day moving average (baseline)
- Day-of-week seasonality (weights per weekday)
- Linear trend (growth/decline)
- Simple confidence intervals (±1 std dev)
"""
from datetime import datetime, timedelta
from statistics import mean, stdev

from db.connection import execute_query


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


WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


# ============================================================
# FETCH HISTORICAL DATA
# ============================================================

def _get_daily_history(kitchen_id, days=90):
    """Get daily order/revenue history."""
    rows = execute_query(
        """
        SELECT
            order_date::text AS date,
            EXTRACT(DOW FROM order_date)::int AS dow,
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
          AND order_date < CURRENT_DATE
        GROUP BY order_date
        ORDER BY order_date
        """,
        (kitchen_id, days),
    )

    return [
        {
            'date': r['date'],
            'dow': _i(r['dow']),
            'orders': _i(r['orders']),
            'revenue': _f(r['revenue']),
        }
        for r in rows
    ]


# ============================================================
# ANALYZE PATTERNS
# ============================================================

def _analyze(history):
    """Extract trend, weekday seasonality, variance."""

    if len(history) < 7:
        return None

    # Overall averages
    orders = [d['orders'] for d in history]
    revenues = [d['revenue'] for d in history]

    avg_orders = mean(orders) if orders else 0
    avg_revenue = mean(revenues) if revenues else 0
    std_orders = stdev(orders) if len(orders) > 1 else 0
    std_revenue = stdev(revenues) if len(revenues) > 1 else 0

    # Weekday seasonality: avg per day-of-week / overall avg
    weekday_orders = {i: [] for i in range(7)}
    weekday_revenue = {i: [] for i in range(7)}

    for d in history:
        weekday_orders[d['dow']].append(d['orders'])
        weekday_revenue[d['dow']].append(d['revenue'])

    weekday_weights = {}
    for dow in range(7):
        avg_dow_orders = mean(weekday_orders[dow]) if weekday_orders[dow] else avg_orders
        avg_dow_revenue = mean(weekday_revenue[dow]) if weekday_revenue[dow] else avg_revenue
        weekday_weights[dow] = {
            'orders': (avg_dow_orders / avg_orders) if avg_orders else 1.0,
            'revenue': (avg_dow_revenue / avg_revenue) if avg_revenue else 1.0,
        }

    # Simple linear trend (last 30 days slope)
    recent = history[-30:] if len(history) >= 30 else history
    trend_slope = 0
    if len(recent) >= 2:
        n = len(recent)
        x = list(range(n))
        y_orders = [d['orders'] for d in recent]
        x_mean = mean(x)
        y_mean = mean(y_orders)
        num = sum((x[i] - x_mean) * (y_orders[i] - y_mean) for i in range(n))
        den = sum((x[i] - x_mean) ** 2 for i in range(n))
        trend_slope = (num / den) if den else 0

    # Recent 7-day moving average (more responsive than 90-day)
    recent_7 = [d['orders'] for d in history[-7:]]
    recent_7_rev = [d['revenue'] for d in history[-7:]]
    base_orders = mean(recent_7) if recent_7 else avg_orders
    base_revenue = mean(recent_7_rev) if recent_7_rev else avg_revenue

    return {
        'avg_orders': round(avg_orders, 1),
        'avg_revenue': round(avg_revenue, 2),
        'std_orders': round(std_orders, 1),
        'std_revenue': round(std_revenue, 2),
        'weekday_weights': weekday_weights,
        'trend_slope': round(trend_slope, 3),
        'base_orders': round(base_orders, 1),
        'base_revenue': round(base_revenue, 2),
        'data_points': len(history),
    }


# ============================================================
# FORECAST
# ============================================================

def forecast(kitchen_id, days_ahead=7):
    """Forecast next N days orders + revenue."""

    history = _get_daily_history(kitchen_id, days=90)

    if len(history) < 7:
        return {
            'error': 'Not enough history. Need at least 7 days of orders.',
            'data_points': len(history),
            'forecast': [],
        }

    analysis = _analyze(history)

    # Generate predictions
    forecast_days = []
    today = datetime.now().date()

    for i in range(1, days_ahead + 1):
        target_date = today + timedelta(days=i)
        dow = target_date.weekday()  # 0 = Monday

        # Convert Python weekday (0=Mon) to Postgres DOW (0=Sun)
        pg_dow = (dow + 1) % 7

        # Base prediction + trend
        trend_effect = analysis['trend_slope'] * (len(history) + i)
        raw_orders = analysis['base_orders'] + trend_effect

        # Apply weekday weight
        weight = analysis['weekday_weights'][pg_dow]
        predicted_orders = max(0, raw_orders * weight['orders'])
        predicted_revenue = max(0, analysis['base_revenue'] * weight['revenue'])

        # Confidence range (±20%)
        margin = 0.2
        forecast_days.append({
            'date': str(target_date),
            'weekday': WEEKDAYS[dow],
            'predicted_orders': round(predicted_orders, 0),
            'predicted_revenue': round(predicted_revenue, 2),
            'range_low_orders': round(predicted_orders * (1 - margin), 0),
            'range_high_orders': round(predicted_orders * (1 + margin), 0),
            'range_low_revenue': round(predicted_revenue * (1 - margin), 2),
            'range_high_revenue': round(predicted_revenue * (1 + margin), 2),
        })

    # Totals
    total_orders = sum(d['predicted_orders'] for d in forecast_days)
    total_revenue = sum(d['predicted_revenue'] for d in forecast_days)

    # Compare to same period last week
    last_week = history[-7:]
    last_week_orders = sum(d['orders'] for d in last_week)
    last_week_revenue = sum(d['revenue'] for d in last_week)

    def _growth(curr, prev):
        if prev == 0:
            return 0
        return round((curr - prev) / prev * 100, 1)

    return {
        'horizon_days': days_ahead,
        'total_predicted_orders': round(total_orders, 0),
        'total_predicted_revenue': round(total_revenue, 2),
        'expected_growth_pct': _growth(total_orders, last_week_orders),
        'last_week_orders': _i(last_week_orders),
        'last_week_revenue': round(last_week_revenue, 2),
        'analysis': {
            'avg_daily_orders': analysis['avg_orders'],
            'avg_daily_revenue': analysis['avg_revenue'],
            'trend': 'growing' if analysis['trend_slope'] > 0.1 else
                     'declining' if analysis['trend_slope'] < -0.1 else 'stable',
            'trend_slope': analysis['trend_slope'],
            'data_points': analysis['data_points'],
        },
        'forecast': forecast_days,
        'daily_history': history[-14:],  # Last 14 days for chart
    }


def hourly_forecast(kitchen_id, day_of_week=None):
    """Predict hourly order distribution for a day."""

    rows = execute_query(
        """
        SELECT
            EXTRACT(HOUR FROM order_time)::int AS hour,
            COUNT(*) AS orders
        FROM orders
        WHERE kitchen_id = %s
          AND order_time IS NOT NULL
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '60 days'
        GROUP BY hour
        ORDER BY hour
        """,
        (kitchen_id,),
    )

    if not rows:
        return []

    total = sum(_i(r['orders']) for r in rows) or 1

    return [
        {
            'hour': _i(r['hour']),
            'label': f"{_i(r['hour']):02d}:00",
            'orders': _i(r['orders']),
            'share_pct': round(_i(r['orders']) / total * 100, 1),
        }
        for r in rows
    ]


def items_forecast(kitchen_id, days_ahead=7, limit=10):
    """Forecast top items demand."""

    rows = execute_query(
        """
        SELECT
            oi.item_name AS name,
            COUNT(DISTINCT oi.order_id) AS orders,
            COALESCE(SUM(oi.quantity), 0) AS qty
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE o.kitchen_id = %s
          AND o.status != 'cancelled'
          AND o.order_date >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY oi.item_name
        ORDER BY qty DESC
        LIMIT %s
        """,
        (kitchen_id, limit),
    )

    # Daily average × forecast days
    result = []
    for r in rows:
        qty_30d = _i(r['qty'])
        daily_avg = qty_30d / 30
        predicted = daily_avg * days_ahead

        result.append({
            'item': r['name'],
            'qty_last_30d': qty_30d,
            'daily_avg': round(daily_avg, 1),
            'predicted_qty': round(predicted, 0),
            'confidence': 'high' if qty_30d > 50 else 'medium' if qty_30d > 10 else 'low',
        })

    return result
