"""Budget management endpoints."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.config import Settings, get_settings
from app.db.models import User
from app.db.repositories.budget_repository import BudgetRepository
from app.schemas.budget import (
    BudgetCreateRequest,
    BudgetResponse,
    BudgetSpendingResponse,
    BudgetUpdateRequest,
)
from app.services.budget_service import BudgetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post(
    "",
    response_model=BudgetSpendingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new budget for a category and date range",
)
def create_budget(
    payload: BudgetCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetSpendingResponse:
    """Create a spending budget for a specific transaction category within a date range.

    The budget tracks actual spending against the limit and returns a status:
    - **under_budget**: spending below 80% of the budget
    - **near_limit**: spending between 80% and 100% of the budget
    - **over_budget**: spending exceeds the budget
    """
    service = BudgetService(BudgetRepository(db))
    try:
        result = service.create_budget(user_id=current_user.id, payload=payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return result


@router.get(
    "",
    response_model=list[BudgetSpendingResponse],
    status_code=status.HTTP_200_OK,
    summary="List all budgets with spending analysis",
)
def list_budgets(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[BudgetSpendingResponse]:
    """List all budgets for the authenticated user, enriched with current spending data."""
    service = BudgetService(BudgetRepository(db))
    return service.list_budgets(user_id=current_user.id)


@router.get(
    "/{budget_id}",
    response_model=BudgetSpendingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific budget with spending analysis",
)
def get_budget(
    budget_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetSpendingResponse:
    """Retrieve a specific budget by ID, ensuring it belongs to the authenticated user."""
    service = BudgetService(BudgetRepository(db))
    result = service.get_budget(user_id=current_user.id, budget_id=budget_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found or access denied.",
        )
    return result


@router.patch(
    "/{budget_id}",
    response_model=BudgetSpendingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing budget",
)
def update_budget(
    budget_id: UUID,
    payload: BudgetUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetSpendingResponse:
    """Update a budget's amount or date range. All fields are optional."""
    service = BudgetService(BudgetRepository(db))
    try:
        result = service.update_budget(
            user_id=current_user.id, budget_id=budget_id, payload=payload
        )
    except ValueError as exc:
        detail = str(exc)
        code = (
            status.HTTP_409_CONFLICT
            if "already exists" in detail
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=detail) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found or access denied.",
        )
    return result


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a budget",
)
def delete_budget(
    budget_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a budget. Does not affect existing transactions."""
    service = BudgetService(BudgetRepository(db))
    deleted = service.delete_budget(user_id=current_user.id, budget_id=budget_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found or access denied.",
        )


# --- AI BUDGET ANALYSIS ENDPOINTS ---

class BudgetAnalysisRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class BudgetAnalysisResponse(BaseModel):
    response: str


@router.post(
    "/analyze",
    response_model=BudgetAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="AI analysis of the user's budget health",
)
def analyze_budgets(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BudgetAnalysisResponse:
    """Get AI-powered analysis of all budgets for the authenticated user.

    The Budget Agent:
    1. Deterministically retrieves all budget data with spending analysis
    2. Passes verified financial context to the LLM
    3. Returns AI-generated budget insights

    All financial numbers are from backend calculations.
    """
    try:
        from app.agents.budget_agent import BudgetAgent
        from app.services.groq_chat_llm import GroqChatLlm

        llm = GroqChatLlm(settings)
        agent = BudgetAgent(session=db, llm=llm)
        result = agent.analyze_all_budgets(user_id=current_user.id)
        return BudgetAnalysisResponse(response=result.get("ai_summary", "No budget data available."))
    except RuntimeError as exc:
        logger.error("LLM provider not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI assistant is not configured. Please contact the administrator.",
        ) from exc
    except Exception as exc:
        logger.error("Budget AI analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Budget analysis is temporarily unavailable. Please try again later.",
        ) from exc


@router.post(
    "/chat",
    response_model=BudgetAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a natural language question about your budgets",
)
def budget_chat(
    payload: BudgetAnalysisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BudgetAnalysisResponse:
    """Ask the Budget Agent a natural language question about your budgets.

    The agent deterministically gathers all budget data, then the AI answers
    using only verified financial context.
    """
    try:
        from app.agents.budget_agent import BudgetAgent
        from app.services.groq_chat_llm import GroqChatLlm

        llm = GroqChatLlm(settings)
        agent = BudgetAgent(session=db, llm=llm)
        response = agent.answer_budget_question(
            user_id=current_user.id,
            question=payload.message,
        )
        return BudgetAnalysisResponse(response=response)
    except RuntimeError as exc:
        logger.error("LLM provider not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI assistant is not configured. Please contact the administrator.",
        ) from exc
    except Exception as exc:
        logger.error("Budget chat failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Budget analysis is temporarily unavailable. Please try again later.",
        ) from exc
