"""Controlled tools used by the Report Agent for deterministic financial queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Transaction, TransactionCategory


@dataclass(frozen=True)
class FinancialSummaryData:
    """Deterministic financial summary for a period. All numbers from verified DB queries."""
    total_income: float
    total_expenses: float
    net_cash_flow: float
    transaction_count: int
    income_count: int
    expense_count: int
    category_breakdown: dict[str, float] = field(default_factory=dict)
    period_start: str = ""
    period_end: str = ""


def get_financial_summary(
    session: Session,
    user_id: UUID,
    period_start,
    period_end,
) -> FinancialSummaryData:
    """Retrieve deterministic financial summary for a date range.
    
    All amounts are from verified DB aggregation queries.
    No LLM involvement in any calculation.
    """
    income_result = session.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00")),
            func.count(Transaction.id),
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
    ).one()
    total_income = income_result[0]
    income_count = income_result[1]

    expense_result = session.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00")),
            func.count(Transaction.id),
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
    ).one()
    total_expenses = expense_result[0]
    expense_count = expense_result[1]

    tx_count = income_count + expense_count

    category_rows = session.execute(
        select(
            TransactionCategory.name,
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00")),
        )
        .join(Transaction, Transaction.category_id == TransactionCategory.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        .group_by(TransactionCategory.name)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()

    category_breakdown = {row[0]: float(row[1]) for row in category_rows}

    return FinancialSummaryData(
        total_income=float(total_income),
        total_expenses=float(total_expenses),
        net_cash_flow=float(total_income - total_expenses),
        transaction_count=tx_count,
        income_count=income_count,
        expense_count=expense_count,
        category_breakdown=category_breakdown,
        period_start=str(period_start),
        period_end=str(period_end),
    )


def get_top_transactions(
    session: Session,
    user_id: UUID,
    period_start,
    period_end,
    limit: int = 5,
) -> list[dict]:
    """Retrieve top expense transactions for the period. Deterministic DB query."""
    rows = session.execute(
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        .order_by(Transaction.amount.desc())
        .limit(limit)
    ).scalars().all()

    return [
        {
            "description": tx.description,
            "amount": float(tx.amount),
            "date": str(tx.transaction_date),
        }
        for tx in rows
    ]
