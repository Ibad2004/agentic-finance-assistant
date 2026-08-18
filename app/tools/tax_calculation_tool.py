"""Controlled tool interface for England Income Tax (2026/27) estimation."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import TaxCalculation
from app.db.repositories.tax_calculation_repository import TaxCalculationRepository
from app.services.tax_calculation_service import TaxCalculationService
from app.tax.uk.england.tax_year_2026_27.schemas import TaxCalculationResult


def estimate_income_tax(
    total_income: Decimal,
    custom_allowance: Decimal | None = None,
) -> TaxCalculationResult:
    """Pure tool function returning a deterministic England Income Tax 2026/27 estimate."""
    service = TaxCalculationService()
    return service.calculate_estimate(
        total_income=total_income,
        custom_allowance=custom_allowance,
    )


def calculate_and_record_tax_estimate(
    session: Session,
    authenticated_user_id: UUID,
    total_income: Decimal,
    custom_allowance: Decimal | None = None,
) -> TaxCalculation:
    """Calculate and persist a tax calculation scoped to the authenticated user."""
    repository = TaxCalculationRepository(session)
    service = TaxCalculationService(repository)
    return service.calculate_and_save(
        user_id=authenticated_user_id,
        total_income=total_income,
        custom_allowance=custom_allowance,
    )
