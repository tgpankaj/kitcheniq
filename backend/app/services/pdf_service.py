"""
KitchenIQ — PDF Export Service
Professional invoice-style report using ReportLab.
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)

from db.connection import execute_query, execute_one


BRAND = colors.HexColor("#2563EB")
DARK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F1F5F9")
SUCCESS = colors.HexColor("#10B981")
DANGER = colors.HexColor("#EF4444")


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


def _inr(v):
    return f"Rs. {_f(v):,.2f}"


def build_pdf(kitchen_id, days=30):
    """Build a PDF report. Returns bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=24, textColor=BRAND, spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    subtitle = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=11, textColor=MUTED, spaceAfter=20,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, textColor=DARK, spaceAfter=10, spaceBefore=20,
        fontName="Helvetica-Bold",
    )
    body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=DARK, leading=14,
    )

    story = []

    # ============================================================
    # Header
    # ============================================================
    story.append(Paragraph("KitchenIQ Business Report", title_style))

    kitchen = execute_one("SELECT name FROM kitchens WHERE id = %s", (kitchen_id,))
    kitchen_name = kitchen['name'] if kitchen else 'Kitchen'

    story.append(Paragraph(
        f"<b>{kitchen_name}</b> &nbsp;·&nbsp; Period: Last {days} days &nbsp;·&nbsp; "
        f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
        subtitle,
    ))

    # ============================================================
    # KPIs
    # ============================================================
    summary = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue,
            COALESCE(SUM(platform_fee) FILTER (WHERE status != 'cancelled'), 0) AS fees,
            COALESCE(SUM(food_cost) FILTER (WHERE status != 'cancelled'), 0) AS food_cost,
            COALESCE(SUM(profit) FILTER (WHERE status != 'cancelled'), 0) AS profit,
            COALESCE(AVG(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS aov
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days),
    )

    revenue = _f(summary['revenue'])
    profit = _f(summary['profit'])
    margin = (profit / revenue * 100) if revenue > 0 else 0

    # KPI grid (2 columns)
    kpi_data = [
        ["Total Revenue", "Net Profit", "Orders", "Avg Order Value"],
        [_inr(revenue), _inr(profit), str(_i(summary['orders'])), _inr(summary['aov'])],
    ]

    kpi_table = Table(kpi_data, colWidths=[42 * mm] * 4)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT),
        ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('TEXTCOLOR', (0, 1), (0, 1), BRAND),
        ('TEXTCOLOR', (1, 1), (1, 1), SUCCESS if profit >= 0 else DANGER),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
    ]))

    story.append(kpi_table)
    story.append(Spacer(1, 8))

    # ============================================================
    # P&L Statement
    # ============================================================
    story.append(Paragraph("Profit &amp; Loss Statement", h2))

    discounts = execute_one(
        "SELECT COALESCE(SUM(discount), 0) AS d FROM orders WHERE kitchen_id = %s AND status != 'cancelled' AND order_date >= CURRENT_DATE - INTERVAL '%s days'",
        (kitchen_id, days),
    )
    packaging = execute_one(
        "SELECT COALESCE(SUM(packaging_cost), 0) AS p FROM orders WHERE kitchen_id = %s AND status != 'cancelled' AND order_date >= CURRENT_DATE - INTERVAL '%s days'",
        (kitchen_id, days),
    )

    pl_data = [
        ["Item", "Amount"],
        ["Gross Revenue", _inr(revenue)],
        ["Less: Discounts", f"- {_inr(discounts['d'])}"],
        ["Net Sales", _inr(revenue - _f(discounts['d']))],
        ["", ""],
        ["Less: Food Cost", f"- {_inr(summary['food_cost'])}"],
        ["Less: Platform Fees", f"- {_inr(summary['fees'])}"],
        ["Less: Packaging", f"- {_inr(packaging['p'])}"],
        ["Net Profit", _inr(profit)],
        ["Profit Margin", f"{margin:.1f}%"],
    ]

    pl_table = Table(pl_data, colWidths=[120 * mm, 60 * mm])
    pl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        # Highlight net sales
        ('FONTNAME', (0, 3), (1, 3), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 3), (-1, 3), LIGHT),
        # Highlight profit
        ('FONTNAME', (0, 8), (1, 8), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 8), (1, 8), SUCCESS if profit >= 0 else DANGER),
        ('BACKGROUND', (0, 8), (-1, 8), LIGHT),
        ('FONTNAME', (0, 9), (1, 9), 'Helvetica-Bold'),
    ]))

    story.append(pl_table)

    # ============================================================
    # Top Dishes
    # ============================================================
    story.append(PageBreak())
    story.append(Paragraph("Top Dishes", h2))

    dishes = execute_query(
        """
        SELECT oi.item_name AS name,
               COUNT(DISTINCT oi.order_id) AS orders,
               COALESCE(SUM(oi.quantity), 0) AS qty,
               COALESCE(SUM(oi.line_total), 0) AS revenue
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE o.kitchen_id = %s
          AND o.status != 'cancelled'
          AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY oi.item_name
        ORDER BY revenue DESC
        LIMIT 15
        """,
        (kitchen_id, days),
    )

    dish_data = [["Dish", "Orders", "Qty Sold", "Revenue"]]
    for d in dishes:
        dish_data.append([
            d['name'][:35],
            str(_i(d['orders'])),
            str(_i(d['qty'])),
            _inr(d['revenue']),
        ])

    dish_table = Table(dish_data, colWidths=[80 * mm, 25 * mm, 25 * mm, 50 * mm])
    dish_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))

    story.append(dish_table)

    # ============================================================
    # Footer note
    # ============================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f"<i>Report generated by KitchenIQ on {datetime.now().strftime('%d %b %Y at %H:%M')}. "
        f"All amounts in INR.</i>",
        ParagraphStyle("Footer", parent=body, fontSize=9, textColor=MUTED),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()