"""Controlled tools used by the Budget Agent for deterministic budget queries."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repositories.budget_repository import BudgetRepository


@dataclass(frozen=True)
class BudgetSpendingData:
    """Deterministic budget spending data for AI context. Read-only, verified data."""
    budget_id: UUID
    category_name: str
    budget_amount: float
    actual_spending: float
    remaining: float
    percentage_used: float
    status: str
    transaction_count: int
    period_start: str
    period_end: str


def get_all_budgets_with_spending(
    session: Session,
    user_id: UUID,
) -> list[BudgetSpendingData]:
    """Retrieve all budgets for a user, enriched with deterministic spending data.
    
    All calculations (spending, percentage, remaining, status) are deterministic.
    Returns verified, read-only data safe for AI context.
    """
    repository = BudgetRepository(session)
    budgets = repository.list_budgets_for_user(user_id)
    
    results = []
    for budget in budgets:
        spending, tx_count = repository.get_spending_for_budget(
            user_id=user_id,
            category_id=budget.category_id,
            period_start=budget.period_start,
            period_end=budget.period_end,
        )
        budget_amount = Decimal(str(budget.budget_amount))
        remaining = budget_amount - spending
        if budget_amount > 0:
            percentage = float((spending / budget_amount).quantize(Decimal("0.0001")))
        else:
            percentage = 0.0
        
        if percentage < 0.80:
            status = "under_budget"
        elif percentage <= 1.00:
            status = "near_limit"
        else:
            status = "over_budget"
        
        category_name = repository.get_category_name(budget.category_id) or "Unknown"
        
        results.append(BudgetSpendingData(
            budget_id=budget.id,
            category_name=category_name,
            budget_amount=float(budget_amount),
            actual_spending=float(spending),
            remaining=float(remaining),
            percentage_used=percentage,
            status=status,
            transaction_count=tx_count,
            period_start=str(budget.period_start),
            period_end=str(budget.period_end),
        ))
    
    return results


def get_budget_spending_detail(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
) -> BudgetSpendingData | None:
    """Retrieve a single budget with spending detail. Returns None if not found or unauthorized."""
    repository = BudgetRepository(session)
    budget = repository.get_budget_for_user(budget_id, user_id)
    if budget is None:
        return None
    
    spending, tx_count = repository.get_spending_for_budget(
        user_id=user_id,
        category_id=budget.category_id,
        period_start=budget.period_start,
        period_end=budget.period_end,
    )
    budget_amount = Decimal(str(budget.budget_amount))
    remaining = budget_amount - spending
    if budget_amount > 0:
        percentage = float((spending / budget_amount).quantize(Decimal("0.0001")))
    else:
        percentage = 0.0
    
    if percentage < 0.80:
        status = "under_budget"
    elif percentage <= 1.00:
        status = "near_limit"
    else:
        status = "over_budget"
    
    category_name = repository.get_category_name(budget.category_id) or "Unknown"
    
    return BudgetSpendingData(
        budget_id=budget.id,
        category_name=category_name,
        budget_amount=float(budget_amount),
        actual_spending=float(spending),
        remaining=float(remaining),
        percentage_used=percentage,
        status=status,
        transaction_count=tx_count,
        period_start=str(budget.period_start),
        period_end=str(budget.period_end),
    )
