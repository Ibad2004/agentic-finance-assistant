"""Budget management endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.db.models import User
from app.db.repositories.budget_repository import BudgetRepository
from app.schemas.budget import (
    BudgetCreateRequest,
    BudgetResponse,
    BudgetSpendingResponse,
    BudgetUpdateRequest,
)
from app.services.budget_service import BudgetService

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
