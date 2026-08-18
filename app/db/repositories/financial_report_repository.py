"""Repository for FinancialReport database operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FinancialReport


class FinancialReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_report(
        self,
        *,
        user_id: UUID,
        report_type: str,
        period_start,
        period_end,
        file_format: str,
        storage_path: str,
        tax_calculation_id: UUID | None = None,
    ) -> FinancialReport:
        report = FinancialReport(
            user_id=user_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            file_format=file_format,
            storage_path=storage_path,
            tax_calculation_id=tax_calculation_id,
        )
        self._session.add(report)
        self._session.flush()
        return report

    def get_report_for_user(self, report_id: UUID, user_id: UUID) -> FinancialReport | None:
        return self._session.scalar(
            select(FinancialReport).where(
                FinancialReport.id == report_id,
                FinancialReport.user_id == user_id,
            )
        )

    def list_reports_for_user(self, user_id: UUID) -> list[FinancialReport]:
        return list(
            self._session.scalars(
                select(FinancialReport)
                .where(FinancialReport.user_id == user_id)
                .order_by(FinancialReport.generated_at.desc())
            )
        )

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
