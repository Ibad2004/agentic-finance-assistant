"""Application service for budget management with spending analysis."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from app.db.repositories.budget_repository import BudgetRepository
from app.schemas.budget import (
    BudgetCreateRequest,
    BudgetResponse,
    BudgetSpendingResponse,
    BudgetUpdateRequest,
)

# Budget status thresholds
UNDER_BUDGET_THRESHOLD = Decimal("0.80")  # 80% — below this is "under_budget"
NEAR_LIMIT_THRESHOLD = Decimal("1.00")   # 100% — between 80% and 100% is "near_limit"
# Above 100% is "over_budget"


def _compute_status(percentage_used: Decimal) -> str:
    """Deterministically classify budget status from percentage used."""
    if percentage_used < UNDER_BUDGET_THRESHOLD:
        return "under_budget"
    if percentage_used <= NEAR_LIMIT_THRESHOLD:
        return "near_limit"
    return "over_budget"


class BudgetService:
    def __init__(self, repository: BudgetRepository) -> None:
        self._repository = repository

    def create_budget(
        self,
        user_id: UUID,
        payload: BudgetCreateRequest,
    ) -> BudgetSpendingResponse:
        if payload.period_end < payload.period_start:
            raise ValueError("period_end must not be before period_start.")

        if self._repository.check_duplicate_budget(
            user_id=user_id,
            category_id=payload.category_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
        ):
            raise ValueError(
                "A budget for this category and date range already exists."
            )

        budget = self._repository.create_budget(
            user_id=user_id,
            category_id=payload.category_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            budget_amount=payload.budget_amount,
        )
        self._repository.commit()

        return self._enrich_with_spending(user_id, budget)

    def list_budgets(self, user_id: UUID) -> list[BudgetSpendingResponse]:
        budgets = self._repository.list_budgets_for_user(user_id)
        return [self._enrich_with_spending(user_id, b) for b in budgets]

    def get_budget(self, user_id: UUID, budget_id: UUID) -> BudgetSpendingResponse | None:
        budget = self._repository.get_budget_for_user(budget_id, user_id)
        if budget is None:
            return None
        return self._enrich_with_spending(user_id, budget)

    def update_budget(
        self,
        user_id: UUID,
        budget_id: UUID,
        payload: BudgetUpdateRequest,
    ) -> BudgetSpendingResponse | None:
        budget = self._repository.get_budget_for_user(budget_id, user_id)
        if budget is None:
            return None

        update_fields = {}
        if payload.budget_amount is not None:
            update_fields["budget_amount"] = payload.budget_amount
        if payload.period_start is not None:
            update_fields["period_start"] = payload.period_start
        if payload.period_end is not None:
            update_fields["period_end"] = payload.period_end

        if update_fields:
            self._repository.update_budget(budget, **update_fields)

            effective_start = update_fields.get("period_start", budget.period_start)
            effective_end = update_fields.get("period_end", budget.period_end)
            if effective_end < effective_start:
                raise ValueError("period_end must not be before period_start.")

            effective_category = budget.category_id
            if self._repository.check_duplicate_budget(
                user_id=user_id,
                category_id=effective_category,
                period_start=effective_start,
                period_end=effective_end,
                exclude_budget_id=budget_id,
            ):
                raise ValueError(
                    "A budget for this category and date range already exists."
                )

            self._repository.commit()

        return self._enrich_with_spending(user_id, budget)

    def delete_budget(self, user_id: UUID, budget_id: UUID) -> bool:
        budget = self._repository.get_budget_for_user(budget_id, user_id)
        if budget is None:
            return False
        self._repository.delete_budget(budget)
        self._repository.commit()
        return True

    def _enrich_with_spending(
        self, user_id: UUID, budget
    ) -> BudgetSpendingResponse:
        spending, tx_count = self._repository.get_spending_for_budget(
            user_id=user_id,
            category_id=budget.category_id,
            period_start=budget.period_start,
            period_end=budget.period_end,
        )

        budget_amount = Decimal(str(budget.budget_amount))
        remaining = budget_amount - spending
        if budget_amount > 0:
            percentage = (spending / budget_amount).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
        else:
            percentage = Decimal("0.0000")

        status = _compute_status(percentage)

        category_name = self._repository.get_category_name(budget.category_id) or "Unknown"

        return BudgetSpendingResponse(
            id=budget.id,
            category_id=budget.category_id,
            category_name=category_name,
            budget_amount=float(budget_amount),
            period_start=budget.period_start,
            period_end=budget.period_end,
            actual_spending=float(spending),
            remaining=float(remaining),
            percentage_used=float(percentage),
            status=status,
            transaction_count=tx_count,
            created_at=budget.created_at,
        )
