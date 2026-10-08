"""
KitchenIQ — Insights Engine
Rule-based business recommendations.

Categories:
- PROMOTE (success)     : High margin + high demand
- OPPORTUNITY (info)    : Growth potential
- OPTIMIZE (warning)    : Cost/margin issues
- REVIEW (danger)       : Underperformers, risks
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


def generate_insights(kitchen_id, days=30):
    """Main entry — returns list of insight dicts sorted by priority."""
    insights = []
    insights += _dish_profitability(kitchen_id, days)
    insights += _platform_commission(kitchen_id, days)
    insights += _discount_analysis(kitchen_id, days)
    insights += _cancellation_analysis(kitchen_id, days)
    insights += _peak_hours(kitchen_id, days)
    insights += _repeat_customers(kitchen_id, days)
    insights += _best_platform(kitchen_id, days)

    # Sort: danger > warning > info > success
    priority = {'danger': 0, 'warning': 1, 'info': 2, 'success': 3}
    insights.sort(key=lambda i: priority.get(i['type'], 99))

    return insights


# ============================================================
# 1. DISH PROFITABILITY
# ============================================================

def _dish_profitability(kitchen_id, days):
    rows = execute_query(
        """
        SELECT
            oi.item_name AS name,
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
        return []

    # Estimated food cost as 40% of revenue (or real recipe cost if available)
    recipe_rows = execute_query(
        """
        SELECT r.menu_item_name AS name,
               COALESCE(SUM(r.quantity_required * i.cost_per_unit), 0) AS unit_cost
        FROM recipes r
        JOIN ingredients i ON i.id = r.ingredient_id
        WHERE r.kitchen_id = %s
        GROUP BY r.menu_item_name
        """,
        (kitchen_id,),
    )
    recipe_map = {r['name']: _f(r['unit_cost']) for r in recipe_rows}

    dishes = []
    for r in rows:
        revenue = _f(r['revenue'])
        qty = _i(r['qty'])
        unit_cost = recipe_map.get(r['name'], revenue / max(qty, 1) * 0.4)
        total_cost = unit_cost * qty
        profit = revenue - total_cost
        margin = (profit / revenue * 100) if revenue > 0 else 0
        dishes.append({
            'name': r['name'],
            'qty': qty,
            'revenue': revenue,
            'profit': profit,
            'margin': margin,
        })

    avg_margin = sum(d['margin'] for d in dishes) / len(dishes) if dishes else 0
    insights = []

    # High-margin winner
    high = [d for d in dishes if d['qty'] >= 3]
    if high:
        best = max(high, key=lambda d: d['margin'])
        if best['margin'] > avg_margin + 8:
            insights.append({
                'type': 'success',
                'category': 'Menu',
                'title': best['name'],
                'reason': f"High profit margin ({best['margin']:.1f}%) vs your average ({avg_margin:.1f}%).",
                'metrics': {
                    'Revenue': f"₹{best['revenue']:,.0f}",
                    'Orders': best['qty'],
                    'Margin': f"{best['margin']:.1f}%",
                },
                'action': "Increase visibility in evening hours. Feature on top of menu.",
            })

    # Low margin with volume
    low = [d for d in dishes if d['qty'] >= 3]
    if low:
        worst = min(low, key=lambda d: d['margin'])
        if worst['margin'] < avg_margin - 8 and worst['margin'] < 40:
            insights.append({
                'type': 'warning',
                'category': 'Menu',
                'title': worst['name'],
                'reason': f"Low margin ({worst['margin']:.1f}%) vs your average ({avg_margin:.1f}%). Consider repricing.",
                'metrics': {
                    'Revenue': f"₹{worst['revenue']:,.0f}",
                    'Orders': worst['qty'],
                    'Margin': f"{worst['margin']:.1f}%",
                },
                'action': "Review recipe cost. Increase price by 5-8% or reduce portion cost.",
            })

    # Critical (below 15% margin with decent revenue)
    for d in dishes:
        if d['revenue'] > 500 and d['margin'] < 15:
            insights.append({
                'type': 'danger',
                'category': 'Menu',
                'title': f"{d['name']} — critically low margin",
                'reason': f"Only {d['margin']:.1f}% margin. Losing money after fees.",
                'metrics': {
                    'Revenue': f"₹{d['revenue']:,.0f}",
                    'Margin': f"{d['margin']:.1f}%",
                },
                'action': "Remove from menu or immediately increase price by 15%.",
            })
            break

    return insights


# ============================================================
# 2. PLATFORM COMMISSION
# ============================================================

def _platform_commission(kitchen_id, days):
    rows = execute_query(
        """
        SELECT
            platform,
            COUNT(*) AS orders,
            COALESCE(SUM(total_amount), 0) AS gross,
            COALESCE(SUM(platform_fee), 0) AS fee,
            COALESCE(SUM(profit), 0) AS profit
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY platform
        HAVING COUNT(*) >= 3
        ORDER BY gross DESC
        """,
        (kitchen_id, days),
    )

    if not rows or len(rows) < 2:
        return []

    insights = []

    # Highest fee platform
    worst = max(rows, key=lambda r: _f(r['fee']) / max(_f(r['gross']), 1))
    fee_pct = (_f(worst['fee']) / max(_f(worst['gross']), 1)) * 100

    if fee_pct > 15:
        insights.append({
            'type': 'warning',
            'category': 'Commission',
            'title': f"{worst['platform'].capitalize()} takes {fee_pct:.1f}% in fees",
            'reason': f"Highest fee platform. {_i(worst['orders'])} orders, ₹{_f(worst['fee']):,.0f} paid in fees.",
            'metrics': {
                'Orders': _i(worst['orders']),
                'Gross': f"₹{_f(worst['gross']):,.0f}",
                'Fees': f"₹{_f(worst['fee']):,.0f}",
                'Fee %': f"{fee_pct:.1f}%",
            },
            'action': f"Shift some promotions to lower-fee channels. Negotiate rates with {worst['platform'].capitalize()}.",
        })

    return insights


# ============================================================
# 3. DISCOUNT ANALYSIS
# ============================================================

def _discount_analysis(kitchen_id, days):
    row = execute_one(
        """
        SELECT
            COALESCE(SUM(total_amount), 0) AS gross,
            COALESCE(SUM(discount), 0) AS discount,
            COUNT(*) FILTER (WHERE discount > 0) AS discounted_orders,
            COUNT(*) AS total_orders
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days),
    )

    gross = _f(row['gross'])
    discount = _f(row['discount'])
    if gross <= 0 or discount <= 0:
        return []

    discount_pct = (discount / gross) * 100

    if discount_pct > 10:
        return [{
            'type': 'warning',
            'category': 'Revenue',
            'title': f"You are losing {discount_pct:.1f}% to discounts",
            'reason': f"₹{discount:,.0f} in discounts on ₹{gross:,.0f} revenue. {_i(row['discounted_orders'])} of {_i(row['total_orders'])} orders had discounts.",
            'metrics': {
                'Discount Amount': f"₹{discount:,.0f}",
                'Discount %': f"{discount_pct:.1f}%",
                'Discounted Orders': _i(row['discounted_orders']),
                'Total Orders': _i(row['total_orders']),
            },
            'action': "Cap discounts at 10%. Target them to new customers only.",
        }]

    return []


# ============================================================
# 4. CANCELLATION
# ============================================================

def _cancellation_analysis(kitchen_id, days):
    row = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COUNT(*) AS total
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days),
    )

    total = _i(row['total'])
    cancelled = _i(row['cancelled'])
    if total < 10:
        return []

    rate = (cancelled / total) * 100

    if rate > 10:
        return [{
            'type': 'danger',
            'category': 'Operations',
            'title': f"Cancellation rate at {rate:.1f}%",
            'reason': f"{cancelled} of {total} orders cancelled. Healthy is under 5%.",
            'metrics': {
                'Cancelled': cancelled,
                'Total Orders': total,
                'Rate': f"{rate:.1f}%",
            },
            'action': "Check prep times vs delivery times. Late food drives cancellations.",
        }]

    return []


# ============================================================
# 5. PEAK HOURS
# ============================================================

def _peak_hours(kitchen_id, days):
    rows = execute_query(
        """
        SELECT
            EXTRACT(HOUR FROM order_time)::int AS hour,
            COUNT(*) AS orders
        FROM orders
        WHERE kitchen_id = %s
          AND order_time IS NOT NULL
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY hour
        ORDER BY orders DESC
        LIMIT 1
        """,
        (kitchen_id, days),
    )

    if not rows:
        return []

    hr = _i(rows[0]['hour'])
    orders = _i(rows[0]['orders'])
    if orders < 3:
        return []

    def fmt_hour(h):
        if h == 0: return '12 AM'
        if h < 12: return f'{h} AM'
        if h == 12: return '12 PM'
        return f'{h - 12} PM'

    return [{
        'type': 'info',
        'category': 'Operations',
        'title': f"Peak ordering hour: {fmt_hour(hr)}",
        'reason': f"{orders} orders in this hour. Focus staffing and promotions here.",
        'metrics': {
            'Peak Hour': fmt_hour(hr),
            'Orders': orders,
        },
        'action': f"Schedule more kitchen staff around {fmt_hour(hr)} and time promos to hit this window.",
    }]


# ============================================================
# 6. REPEAT CUSTOMERS
# ============================================================

def _repeat_customers(kitchen_id, days):
    row = execute_one(
        """
        WITH stats AS (
            SELECT customer_phone, COUNT(*) AS freq
            FROM orders
            WHERE kitchen_id = %s
              AND customer_phone IS NOT NULL
              AND status != 'cancelled'
              AND order_date >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY customer_phone
        )
        SELECT
            COUNT(*) FILTER (WHERE freq >= 2) AS repeat_c,
            COUNT(*) AS total_c
        FROM stats
        """,
        (kitchen_id, days),
    )

    total = _i(row['total_c'])
    repeat = _i(row['repeat_c'])
    if total < 10:
        return []

    pct = (repeat / total) * 100

    if pct > 30:
        return [{
            'type': 'success',
            'category': 'Customers',
            'title': f"Strong loyalty — {pct:.1f}% repeat customers",
            'reason': f"{repeat} of {total} customers ordered more than once.",
            'metrics': {
                'Repeat Customers': repeat,
                'Total Customers': total,
                'Repeat Rate': f"{pct:.1f}%",
            },
            'action': "Launch a loyalty program to convert the rest into repeat buyers.",
        }]
    elif pct < 15:
        return [{
            'type': 'warning',
            'category': 'Customers',
            'title': f"Low retention — only {pct:.1f}% return",
            'reason': f"{repeat} of {total} customers are repeat buyers. Most order once.",
            'metrics': {
                'Repeat Customers': repeat,
                'Total Customers': total,
                'Repeat Rate': f"{pct:.1f}%",
            },
            'action': "Add a follow-up coupon after first order. Investigate why customers don't return.",
        }]

    return []


# ============================================================
# 7. BEST PLATFORM
# ============================================================

def _best_platform(kitchen_id, days):
    rows = execute_query(
        """
        SELECT platform, COALESCE(SUM(profit), 0) AS profit
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY platform
        ORDER BY profit DESC
        LIMIT 1
        """,
        (kitchen_id, days),
    )

    if not rows:
        return []

    best = rows[0]
    if _f(best['profit']) <= 0:
        return []

    return [{
        'type': 'info',
        'category': 'Commission',
        'title': f"{best['platform'].capitalize()} is your most profitable channel",
        'reason': f"₹{_f(best['profit']):,.0f} net profit from this platform.",
        'metrics': {
            'Platform': best['platform'].capitalize(),
            'Profit': f"₹{_f(best['profit']):,.0f}",
        },
        'action': f"Invest more marketing on {best['platform'].capitalize()} to grow volume.",
    }]