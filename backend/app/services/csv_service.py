"""
KitchenIQ — CSV Service
Parses and validates uploaded CSV orders.
"""
import pandas as pd
from datetime import datetime, date, time
from io import StringIO

from db.connection import execute_query, execute_one


REQUIRED_COLUMNS = ['order_date', 'item_name', 'unit_price']
OPTIONAL_COLUMNS = ['order_id', 'order_time', 'platform', 'customer_phone',
                    'customer_name', 'quantity', 'discount', 'platform_fee',
                    'food_cost', 'status']


def parse_csv(file_bytes):
    """Parse CSV bytes into DataFrame. Returns (df, error)."""
    try:
        text = file_bytes.decode('utf-8-sig')
        df = pd.read_csv(StringIO(text))
    except UnicodeDecodeError:
        return None, "File must be UTF-8 encoded text (CSV)"

    if df.empty:
        return None, "CSV file is empty"

    # Normalize columns
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # Validate required
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return None, f"Missing required columns: {', '.join(missing)}"

    return df, None


def process_orders(kitchen_id, df):
    """Insert orders from DataFrame. Returns dict with counts."""
    created = 0
    failed = 0
    errors = []

    # Group by order_id if present, else each row is an order
    has_order_id = 'order_id' in df.columns

    if has_order_id:
        groups = df.groupby('order_id', sort=False)
    else:
        # Each row = 1 order; assign synthetic IDs
        df = df.copy()
        df['order_id'] = [f"row_{i+1}" for i in range(len(df))]
        groups = df.groupby('order_id', sort=False)

    for order_id, group in groups:
        try:
            _insert_order(kitchen_id, order_id, group)
            created += 1
        except Exception as e:
            failed += 1
            errors.append(f"{order_id}: {str(e)[:80]}")

    return {
        'created': created,
        'failed': failed,
        'errors': errors[:10],
    }


def _safe_float(v, default=0):
    try:
        if pd.isna(v):
            return default
        return round(float(v), 2)
    except (ValueError, TypeError):
        return default


def _safe_int(v, default=1):
    try:
        if pd.isna(v):
            return default
        return int(v)
    except (ValueError, TypeError):
        return default


def _insert_order(kitchen_id, order_id, group):
    """Insert one order + its items."""
    first = group.iloc[0]

    # Parse date
    try:
        od = pd.to_datetime(first['order_date']).date()
    except Exception:
        raise ValueError(f"Invalid order_date: {first['order_date']}")

    # Parse time (optional)
    order_time = None
    if 'order_time' in first and pd.notna(first.get('order_time')):
        try:
            order_time = pd.to_datetime(str(first['order_time'])).time()
        except Exception:
            order_time = None

    platform = str(first.get('platform') or 'manual').strip().lower()
    customer_phone = str(first.get('customer_phone') or '').strip() or None
    customer_name = str(first.get('customer_name') or '').strip() or None
    status = str(first.get('status') or 'delivered').strip().lower()
    ext_order_id = str(order_id) if not str(order_id).startswith('row_') else None

    # Aggregate
    total_amount = 0.0
    total_discount = 0.0
    total_platform_fee = 0.0
    total_food_cost = 0.0

    for _, row in group.iterrows():
        qty = _safe_int(row.get('quantity', 1))
        price = _safe_float(row.get('unit_price'))
        total_amount += qty * price
        total_discount += _safe_float(row.get('discount'))
        total_platform_fee += _safe_float(row.get('platform_fee'))
        total_food_cost += _safe_float(row.get('food_cost'))

    net_revenue = total_amount - total_discount - total_platform_fee
    profit = net_revenue - total_food_cost

    # Dedup check
    if ext_order_id:
        existing = execute_one(
            """
            SELECT id FROM orders
            WHERE kitchen_id = %s AND platform = %s AND external_order_id = %s
            """,
            (kitchen_id, platform, ext_order_id),
        )
        if existing:
            return  # Skip duplicate

    # Insert order
    order_row = execute_one(
        """
        INSERT INTO orders (
            kitchen_id, external_order_id, platform,
            order_date, order_time, customer_phone, customer_name,
            total_amount, discount, platform_fee, food_cost,
            net_revenue, profit, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            kitchen_id, ext_order_id, platform,
            od, order_time, customer_phone, customer_name,
            round(total_amount, 2), round(total_discount, 2),
            round(total_platform_fee, 2), round(total_food_cost, 2),
            round(net_revenue, 2), round(profit, 2), status,
        ),
    )

    order_db_id = order_row['id']

    # Insert order items
    for _, row in group.iterrows():
        item_name = str(row['item_name']).strip()
        qty = _safe_int(row.get('quantity', 1))
        price = _safe_float(row.get('unit_price'))

        execute_query(
            """
            INSERT INTO order_items (order_id, item_name, quantity, unit_price, line_total)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (order_db_id, item_name, qty, price, qty * price),
            fetch=False,
        )