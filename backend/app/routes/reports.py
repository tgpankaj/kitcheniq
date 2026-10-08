"""
KitchenIQ — Reports Routes
"""
from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import csv
from io import StringIO

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.services.excel_service import build_workbook
from app.services.pdf_service import build_pdf


reports_bp = Blueprint('reports', __name__)


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


@reports_bp.route('/summary', methods=['GET'])
@token_required
def summary():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 30))
        if days not in (7, 30, 90, 365):
            days = 30
    except (ValueError, TypeError):
        days = 30

    row = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue,
            COALESCE(SUM(discount) FILTER (WHERE status != 'cancelled'), 0) AS discounts,
            COALESCE(SUM(platform_fee) FILTER (WHERE status != 'cancelled'), 0) AS fees,
            COALESCE(SUM(food_cost) FILTER (WHERE status != 'cancelled'), 0) AS food_cost,
            COALESCE(SUM(profit) FILTER (WHERE status != 'cancelled'), 0) AS profit,
            COALESCE(AVG(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS aov,
            COUNT(DISTINCT customer_phone) FILTER (WHERE status != 'cancelled' AND customer_phone IS NOT NULL) AS customers
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days),
    )

    revenue = _f(row['revenue'])
    profit = _f(row['profit'])
    margin = (profit / revenue * 100) if revenue > 0 else 0

    return jsonify({
        'period_days': days,
        'orders': _i(row['orders']),
        'cancelled': _i(row['cancelled']),
        'revenue': round(revenue, 2),
        'discounts': round(_f(row['discounts']), 2),
        'platform_fees': round(_f(row['fees']), 2),
        'food_cost': round(_f(row['food_cost']), 2),
        'profit': round(profit, 2),
        'margin_pct': round(margin, 1),
        'avg_order_value': round(_f(row['aov']), 2),
        'unique_customers': _i(row['customers']),
    })


@reports_bp.route('/daily', methods=['GET'])
@token_required
def daily():
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
            order_date::text AS date,
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue,
            COALESCE(SUM(discount) FILTER (WHERE status != 'cancelled'), 0) AS discounts,
            COALESCE(SUM(platform_fee) FILTER (WHERE status != 'cancelled'), 0) AS fees,
            COALESCE(SUM(food_cost) FILTER (WHERE status != 'cancelled'), 0) AS food_cost,
            COALESCE(SUM(profit) FILTER (WHERE status != 'cancelled'), 0) AS profit
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY order_date
        ORDER BY order_date DESC
        """,
        (kitchen_id, days),
    )

    return jsonify([
        {
            'date': r['date'],
            'orders': _i(r['orders']),
            'cancelled': _i(r['cancelled']),
            'revenue': round(_f(r['revenue']), 2),
            'discounts': round(_f(r['discounts']), 2),
            'platform_fees': round(_f(r['fees']), 2),
            'food_cost': round(_f(r['food_cost']), 2),
            'profit': round(_f(r['profit']), 2),
        }
        for r in rows
    ])


@reports_bp.route('/export', methods=['GET'])
@token_required
def export_csv():
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
            o.id, o.external_order_id, o.platform,
            o.order_date::text AS date, o.order_time::text AS time,
            o.customer_phone, o.customer_name,
            o.total_amount, o.discount, o.tax, o.platform_fee,
            o.packaging_cost, o.food_cost, o.net_revenue, o.profit, o.status
        FROM orders o
        WHERE o.kitchen_id = %s
          AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY o.order_date DESC, o.id DESC
        """,
        (kitchen_id, days),
    )

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'Order ID', 'External ID', 'Platform', 'Date', 'Time',
        'Customer Phone', 'Customer Name',
        'Gross Amount', 'Discount', 'Tax', 'Platform Fee',
        'Packaging Cost', 'Food Cost', 'Net Revenue', 'Profit', 'Status',
    ])

    for r in rows:
        writer.writerow([
            r['id'], r['external_order_id'] or '', r['platform'] or '',
            r['date'], (r['time'] or '')[:8],
            r['customer_phone'] or '', r['customer_name'] or '',
            _f(r['total_amount']), _f(r['discount']), _f(r['tax']), _f(r['platform_fee']),
            _f(r['packaging_cost']), _f(r['food_cost']), _f(r['net_revenue']), _f(r['profit']),
            r['status'] or 'delivered',
        ])

    csv_data = buf.getvalue()
    filename = f"kitcheniq-orders-{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'text/csv; charset=utf-8',
        },
    )


@reports_bp.route('/export-excel', methods=['GET'])
@token_required
def export_excel():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 30))
        if days not in (7, 30, 90, 365):
            days = 30
    except (ValueError, TypeError):
        days = 30

    try:
        data = build_workbook(kitchen_id, days)
    except Exception as e:
        return jsonify({'error': f'Excel generation failed: {str(e)}'}), 500

    filename = f"kitcheniq-report-{datetime.now().strftime('%Y%m%d')}.xlsx"

    return Response(
        data,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@reports_bp.route('/export-pdf', methods=['GET'])
@token_required
def export_pdf():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 30))
        if days not in (7, 30, 90, 365):
            days = 30
    except (ValueError, TypeError):
        days = 30

    try:
        data = build_pdf(kitchen_id, days)
    except Exception as e:
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500

    filename = f"kitcheniq-report-{datetime.now().strftime('%Y%m%d')}.pdf"

    return Response(
        data,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
