"""Repository for persisting and retrieving deterministic TaxCalculation records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TaxCalculation
from app.tax.uk.england.tax_year_2026_27.schemas import TaxCalculationResult


class TaxCalculationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_tax_calculation(
        self,
        user_id: UUID,
        result: TaxCalculationResult,
    ) -> TaxCalculation:
        calculation = TaxCalculation(
            user_id=user_id,
            tax_year=result.tax_year,
            rules_version=result.rules_version,
            total_income=result.total_income,
            total_allowances=result.total_allowances,
            taxable_income=result.taxable_income,
            income_tax_due=result.income_tax_due,
            assumptions=result.assumptions,
            limitations=result.limitations,
            calculation_details=result.calculation_details,
        )
        self._session.add(calculation)
        self._session.flush()
        return calculation

    def get_by_id(self, calculation_id: UUID, user_id: UUID) -> TaxCalculation | None:
        return self._session.scalar(
            select(TaxCalculation).where(
                TaxCalculation.id == calculation_id,
                TaxCalculation.user_id == user_id,
            )
        )

    def list_for_user(self, user_id: UUID) -> list[TaxCalculation]:
        return list(
            self._session.scalars(
                select(TaxCalculation)
                .where(TaxCalculation.user_id == user_id)
                .order_by(TaxCalculation.calculated_at.desc())
            )
        )

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
