"""Tax endpoints for income tax estimation and retrieval."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.agents.tax_agent import TaxAgent
from app.db.models import User
from app.schemas.tax import TaxCalculationResponse, TaxEstimateRequest
from app.tax.uk.england.tax_year_2026_27.calculator import (
    calculate_england_income_tax_2026_27,
)

router = APIRouter(prefix="/tax", tags=["Tax"])


@router.post(
    "/estimate",
    response_model=TaxCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate England Income Tax for the authenticated user",
)
def estimate_tax(
    payload: TaxEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxCalculationResponse:
    """Estimate income tax and persist the result for the authenticated user."""

    agent = TaxAgent(db)

    tax_calculation = agent.calculate_and_save(
        user_id=current_user.id,
        total_income=payload.total_income,
        custom_allowance=payload.custom_allowance,
    )

    # Recompute the engine result to return the structured tax result
    # with the persisted metadata (id, user_id, calculated_at).
    engine_result = calculate_england_income_tax_2026_27(
        total_income=payload.total_income,
        custom_allowance=payload.custom_allowance,
    )

    return TaxCalculationResponse.from_engine_result(
        engine_result,
        id=tax_calculation.id,
        user_id=tax_calculation.user_id,
        calculated_at=tax_calculation.calculated_at,
    )


@router.get(
    "/calculations",
    response_model=list[TaxCalculationResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tax calculations for the authenticated user",
)
def list_tax_calculations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaxCalculationResponse]:
    """List tax calculations scoped to the authenticated user."""

    from app.db.repositories.tax_calculation_repository import (
        TaxCalculationRepository,
    )

    repository = TaxCalculationRepository(db)

    calculations = repository.list_for_user(
        user_id=current_user.id,
    )

    return [
        TaxCalculationResponse.from_engine_result(
            calculate_england_income_tax_2026_27(
                total_income=Decimal(str(calc.total_income)),
                custom_allowance=Decimal(str(calc.total_allowances)),
            ),
            id=calc.id,
            user_id=calc.user_id,
            calculated_at=calc.calculated_at,
        )
        for calc in calculations
    ]


@router.get(
    "/calculations/{calculation_id}",
    response_model=TaxCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific tax calculation by ID for the authenticated user",
)
def get_tax_calculation(
    calculation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxCalculationResponse:
    """Get a tax calculation by ID, ensuring it belongs to the authenticated user."""

    from app.db.repositories.tax_calculation_repository import (
        TaxCalculationRepository,
    )

    repository = TaxCalculationRepository(db)

    calculation = repository.get_by_id(
        calculation_id=calculation_id,
        user_id=current_user.id,
    )

    if calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax calculation not found or access denied.",
        )

    recomputed_result = calculate_england_income_tax_2026_27(
        total_income=Decimal(str(calculation.total_income)),
        custom_allowance=Decimal(str(calculation.total_allowances)),
    )

    return TaxCalculationResponse.from_engine_result(
        recomputed_result,
        id=calculation.id,
        user_id=calculation.user_id,
        calculated_at=calculation.calculated_at,
    )