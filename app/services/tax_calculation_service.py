"""Application service for coordinating deterministic tax calculation and persistence."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.db.models import TaxCalculation
from app.db.repositories.tax_calculation_repository import TaxCalculationRepository
from app.tax.uk.england.tax_year_2026_27.calculator import calculate_england_income_tax_2026_27
from app.tax.uk.england.tax_year_2026_27.schemas import TaxCalculationResult


class TaxCalculationService:
    """Orchestrates deterministic tax calculations and user-scoped database persistence."""

    def __init__(self, repository: TaxCalculationRepository | None = None) -> None:
        self._repository = repository

    def calculate_estimate(
        self,
        total_income: Decimal,
        custom_allowance: Decimal | None = None,
    ) -> TaxCalculationResult:
        """Pure calculation of England Income Tax 2026/27 without database interaction."""
        return calculate_england_income_tax_2026_27(
            total_income=total_income,
            custom_allowance=custom_allowance,
        )

    def calculate_and_save(
        self,
        user_id: UUID,
        total_income: Decimal,
        custom_allowance: Decimal | None = None,
    ) -> TaxCalculation:
        """Calculate England Income Tax and persist the result scoped to the authenticated user."""
        if self._repository is None:
            raise RuntimeError("A TaxCalculationRepository is required to persist calculations.")

        result = self.calculate_estimate(
            total_income=total_income,
            custom_allowance=custom_allowance,
        )
        calculation = self._repository.save_tax_calculation(
            user_id=user_id,
            result=result,
        )
        self._repository.commit()
        return calculation

    def get_calculation(self, calculation_id: UUID, user_id: UUID) -> TaxCalculation | None:
        """Retrieve a specific tax calculation verifying user ownership."""
        if self._repository is None:
            raise RuntimeError("A TaxCalculationRepository is required to retrieve calculations.")
        return self._repository.get_by_id(calculation_id=calculation_id, user_id=user_id)

    def list_calculations(self, user_id: UUID) -> list[TaxCalculation]:
        """List all tax calculations for the authenticated user."""
        if self._repository is None:
            raise RuntimeError("A TaxCalculationRepository is required to list calculations.")
        return self._repository.list_for_user(user_id=user_id)
