"""Repository for Budget database operations."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Budget, Transaction, TransactionCategory


class BudgetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_budget(
        self,
        user_id: UUID,
        category_id: UUID,
        period_start,
        period_end,
        budget_amount: Decimal,
    ) -> Budget:
        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            period_start=period_start,
            period_end=period_end,
            budget_amount=budget_amount,
        )
        self._session.add(budget)
        self._session.flush()
        return budget

    def get_budget_for_user(self, budget_id: UUID, user_id: UUID) -> Budget | None:
        return self._session.scalar(
            select(Budget).where(
                Budget.id == budget_id,
                Budget.user_id == user_id,
            )
        )

    def list_budgets_for_user(self, user_id: UUID) -> list[Budget]:
        return list(
            self._session.scalars(
                select(Budget)
                .where(Budget.user_id == user_id)
                .order_by(Budget.created_at.desc())
            )
        )

    def update_budget(self, budget: Budget, **fields) -> Budget:
        for key, value in fields.items():
            if value is not None:
                setattr(budget, key, value)
        self._session.flush()
        return budget

    def delete_budget(self, budget: Budget) -> None:
        self._session.delete(budget)
        self._session.flush()

    def get_spending_for_budget(
        self,
        user_id: UUID,
        category_id: UUID,
        period_start,
        period_end,
    ) -> tuple[Decimal, int]:
        """Return (total_spending, transaction_count) for the given category and date range."""
        result = self._session.execute(
            select(
                func.coalesce(func.sum(Transaction.amount), Decimal("0.00")),
                func.count(Transaction.id),
            ).where(
                Transaction.user_id == user_id,
                Transaction.category_id == category_id,
                Transaction.transaction_type == "expense",
                Transaction.transaction_date >= period_start,
                Transaction.transaction_date <= period_end,
            )
        )
        row = result.one()
        return row[0], row[1]

    def get_category_name(self, category_id: UUID) -> str | None:
        cat = self._session.scalar(
            select(TransactionCategory.name).where(
                TransactionCategory.id == category_id
            )
        )
        return cat

    def check_duplicate_budget(
        self,
        user_id: UUID,
        category_id: UUID,
        period_start,
        period_end,
        exclude_budget_id: UUID | None = None,
    ) -> bool:
        """Check if a budget with the same category and overlapping period already exists."""
        statement = select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.period_start == period_start,
            Budget.period_end == period_end,
        )
        if exclude_budget_id is not None:
            statement = statement.where(Budget.id != exclude_budget_id)
        return self._session.scalar(statement) is not None

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
