"""Deterministic PDF report generation using reportlab."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def generate_monthly_summary_pdf(
    *,
    user_email: str,
    period_start: date,
    period_end: date,
    total_income: Decimal,
    total_expenses: Decimal,
    transaction_count: int,
    category_breakdown: dict[str, Decimal],
) -> bytes:
    """Generate a deterministic monthly financial summary PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceAfter=6,
        spaceBefore=12,
    )
    body_style = styles["Normal"]
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=body_style,
        fontSize=8,
        textColor=colors.grey,
        spaceBefore=16,
    )

    elements.append(Paragraph("Monthly Financial Summary", title_style))
    elements.append(
        Paragraph(
            f"Period: {period_start.strftime('%d %B %Y')} - {period_end.strftime('%d %B %Y')}",
            subtitle_style,
        )
    )
    elements.append(Paragraph(f"Generated for: {user_email}", subtitle_style))
    elements.append(Spacer(1, 8 * mm))

    net_amount = total_income - total_expenses

    summary_data = [
        ["Metric", "Amount (GBP)"],
        ["Total Income", f"\u00a3{total_income:,.2f}"],
        ["Total Expenses", f"\u00a3{total_expenses:,.2f}"],
        ["Net Amount", f"\u00a3{net_amount:,.2f}"],
        ["Transaction Count", str(transaction_count)],
    ]

    summary_table = Table(summary_data, colWidths=[120, 120])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(Paragraph("Financial Summary", heading_style))
    elements.append(summary_table)
    elements.append(Spacer(1, 6 * mm))

    if category_breakdown:
        elements.append(Paragraph("Expense Breakdown by Category", heading_style))
        breakdown_data = [["Category", "Amount (GBP)", "% of Total"]]
        sorted_categories = sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)
        for cat_name, cat_amount in sorted_categories:
            pct = (cat_amount / total_expenses * 100) if total_expenses > 0 else Decimal("0")
            breakdown_data.append([
                cat_name,
                f"\u00a3{cat_amount:,.2f}",
                f"{pct:.1f}%",
            ])

        breakdown_table = Table(breakdown_data, colWidths=[140, 100, 80])
        breakdown_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(breakdown_table)
        elements.append(Spacer(1, 6 * mm))

    disclaimer_text = (
        "DISCLAIMER: This report is generated from user-imported data and is provided for "
        "informational purposes only. It does not constitute financial advice, a tax "
        "determination, or an official HMRC assessment. All figures are based on transactions "
        "recorded by the user and may not reflect complete financial activity."
    )
    elements.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(elements)
    return buffer.getvalue()
