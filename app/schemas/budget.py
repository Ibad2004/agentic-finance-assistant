"""Pydantic schemas for budget management."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetCreateRequest(BaseModel):
    """Request to create a new budget for a category within a date range."""

    category_id: UUID
    period_start: date
    period_end: date
    budget_amount: Decimal = Field(ge=0, description="Budget limit amount (must be non-negative)")

    @field_validator("budget_amount")
    @classmethod
    def must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("budget_amount must be greater than zero.")
        return value


class BudgetUpdateRequest(BaseModel):
    """Request to update an existing budget."""

    budget_amount: Decimal | None = Field(default=None, ge=0, description="Updated budget limit")
    period_start: date | None = None
    period_end: date | None = None

    @field_validator("budget_amount")
    @classmethod
    def must_be_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("budget_amount must be greater than zero.")
        return value


class BudgetResponse(BaseModel):
    """Response for a budget record."""

    id: UUID
    category_id: UUID
    category_name: str
    budget_amount: float
    period_start: date
    period_end: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetSpendingResponse(BaseModel):
    """Response for a budget with spending analysis."""

    id: UUID
    category_id: UUID
    category_name: str
    budget_amount: float
    period_start: date
    period_end: date
    actual_spending: float
    remaining: float
    percentage_used: float
    status: str
    transaction_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
