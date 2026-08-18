"""Application service for financial report generation and retrieval."""

from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import Transaction, TransactionCategory
from app.db.repositories.financial_report_repository import FinancialReportRepository
from app.schemas.report import ReportGenerateRequest, ReportDetailResponse, ReportResponse
from app.services.pdf_report_service import generate_monthly_summary_pdf


REPORTS_DIR = "reports"


def _ensure_reports_dir() -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return REPORTS_DIR


def _get_transaction_summary(
    session: Session,
    user_id,
    period_start,
    period_end,
) -> tuple[Decimal, Decimal, int, dict[str, Decimal]]:
    """Return (total_income, total_expenses, tx_count, category_breakdown) for the period."""
    from sqlalchemy import func

    income_result = session.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00")),
            func.count(Transaction.id),
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
    ).one()
    total_income = income_result[0]
    income_count = income_result[1]

    expense_result = session.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00")),
            func.count(Transaction.id),
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
    ).one()
    total_expenses = expense_result[0]
    expense_count = expense_result[1]

    tx_count = income_count + expense_count

    category_rows = session.execute(
        select(
            TransactionCategory.name,
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00")),
        )
        .join(Transaction, Transaction.category_id == TransactionCategory.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        .group_by(TransactionCategory.name)
    ).all()

    category_breakdown = {row[0]: row[1] for row in category_rows}

    return total_income, total_expenses, tx_count, category_breakdown


from sqlalchemy import select  # noqa: E402


class ReportService:
    def __init__(self, session: Session, repository: FinancialReportRepository) -> None:
        self._session = session
        self._repository = repository

    def generate_report(
        self,
        user_id,
        user_email: str,
        payload: ReportGenerateRequest,
    ) -> ReportDetailResponse:
        if payload.period_end < payload.period_start:
            raise ValueError("period_end must not be before period_start.")

        total_income, total_expenses, tx_count, category_breakdown = _get_transaction_summary(
            self._session, user_id, payload.period_start, payload.period_end,
        )

        pdf_bytes = generate_monthly_summary_pdf(
            user_email=user_email,
            period_start=payload.period_start,
            period_end=payload.period_end,
            total_income=total_income,
            total_expenses=total_expenses,
            transaction_count=tx_count,
            category_breakdown=category_breakdown,
        )

        reports_dir = _ensure_reports_dir()
        filename = f"{payload.report_type}_{user_id}_{uuid4().hex[:8]}.pdf"
        storage_path = os.path.join(reports_dir, filename)

        with open(storage_path, "wb") as f:
            f.write(pdf_bytes)

        report = self._repository.save_report(
            user_id=user_id,
            report_type=payload.report_type,
            period_start=payload.period_start,
            period_end=payload.period_end,
            file_format="pdf",
            storage_path=storage_path,
        )
        self._repository.commit()

        return ReportDetailResponse(
            id=report.id,
            report_type=report.report_type,
            period_start=report.period_start,
            period_end=report.period_end,
            file_format=report.file_format,
            storage_path=report.storage_path,
            generated_at=report.generated_at,
            total_income=float(total_income),
            total_expenses=float(total_expenses),
            net_amount=float(total_income - total_expenses),
            transaction_count=tx_count,
            category_breakdown={k: float(v) for k, v in category_breakdown.items()},
        )

    def list_reports(self, user_id) -> list[ReportResponse]:
        reports = self._repository.list_reports_for_user(user_id)
        return [
            ReportResponse(
                id=r.id,
                report_type=r.report_type,
                period_start=r.period_start,
                period_end=r.period_end,
                file_format=r.file_format,
                storage_path=r.storage_path,
                generated_at=r.generated_at,
            )
            for r in reports
        ]

    def get_report(self, user_id, report_id) -> ReportResponse | None:
        report = self._repository.get_report_for_user(report_id, user_id)
        if report is None:
            return None
        return ReportResponse(
            id=report.id,
            report_type=report.report_type,
            period_start=report.period_start,
            period_end=report.period_end,
            file_format=report.file_format,
            storage_path=report.storage_path,
            generated_at=report.generated_at,
        )
