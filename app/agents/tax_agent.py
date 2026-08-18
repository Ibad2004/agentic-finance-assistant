"""Tax Agent for coordinating England Income Tax estimation workflow."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.tools.tax_calculation_tool import calculate_and_record_tax_estimate


class TaxAgent:
    """Coordinates tax calculation workflow using deterministic engine."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def calculate_and_save(
        self,
        user_id: UUID,
        total_income: float | int | Decimal,
        custom_allowance: float | int | Decimal | None = None,
    ):
        """Calculate England Income Tax and persist the result for the user.

        Args:
            user_id: The authenticated user's ID.
            total_income: Total income for the tax year.
            custom_allowance: Optional custom allowance.

        Returns:
            The persisted TaxCalculation model.
        """
        from decimal import Decimal

        # Ensure Decimal type for compatibility with the tool
        total_income_dec = Decimal(str(total_income))
        custom_allowance_dec = (
            Decimal(str(custom_allowance)) if custom_allowance is not None else None
        )

        return calculate_and_record_tax_estimate(
            session=self._session,
            authenticated_user_id=user_id,
            total_income=total_income_dec,
            custom_allowance=custom_allowance_dec,
        )