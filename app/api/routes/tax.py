"""Tax endpoints for income tax estimation and retrieval."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.agents.tax_agent import TaxAgent
from app.db.models import User
from app.schemas.tax import TaxCalculationResponse, TaxEstimateRequest

if TYPE_CHECKING:
    from app.config import Settings

from app.config import get_settings
from app.tax.uk.england.tax_year_2026_27.calculator import (
    calculate_england_income_tax_2026_27,
)

logger = logging.getLogger(__name__)

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


# --- AI TAX EXPLANATION ENDPOINTS ---

class TaxExplanationRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class TaxExplanationResponse(BaseModel):
    response: str


@router.post(
    "/explain/{calculation_id}",
    response_model=TaxExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="AI explanation of a specific tax calculation",
)
def explain_tax(
    calculation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: "Settings" = Depends(get_settings),
) -> TaxExplanationResponse:
    """Get AI-powered explanation of a specific tax calculation.

    The Tax Agent:
    1. Retrieves the persisted tax calculation (deterministic)
    2. Passes verified tax data to the LLM
    3. Returns AI-generated explanation in plain language

    The AI does NOT re-calculate tax. It only explains the existing result.
    """
    try:
        from app.services.groq_chat_llm import GroqChatLlm

        llm = GroqChatLlm(settings)
        agent = TaxAgent(session=db, llm=llm)
        result = agent.explain_tax(
            user_id=current_user.id,
            calculation_id=calculation_id,
        )
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"],
            )
        return TaxExplanationResponse(response=result.get("ai_explanation", "Explanation not available."))
    except HTTPException:
        raise
    except RuntimeError as exc:
        logger.error("LLM provider not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI assistant is not configured. Please contact the administrator.",
        ) from exc
    except Exception as exc:
        logger.error("Tax explanation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Tax explanation is temporarily unavailable. Please try again later.",
        ) from exc


@router.post(
    "/chat",
    response_model=TaxExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a natural language question about your tax",
)
def tax_chat(
    payload: TaxExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: "Settings" = Depends(get_settings),
) -> TaxExplanationResponse:
    """Ask the Tax Agent a natural language question about your tax situation.

    The agent retrieves the latest tax calculation (deterministic), then the
    AI answers using only verified tax data.
    """
    try:
        from app.services.groq_chat_llm import GroqChatLlm

        llm = GroqChatLlm(settings)
        agent = TaxAgent(session=db, llm=llm)
        response = agent.answer_tax_question(
            user_id=current_user.id,
            question=payload.question,
        )
        return TaxExplanationResponse(response=response)
    except RuntimeError as exc:
        logger.error("LLM provider not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI assistant is not configured. Please contact the administrator.",
        ) from exc
    except Exception as exc:
        logger.error("Tax chat failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Tax explanation is temporarily unavailable. Please try again later.",
        ) from exc