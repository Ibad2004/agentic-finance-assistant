"""Controlled tools for gathering cross-domain financial context."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Budget, TaxCalculation, Transaction, TransactionCategory


@dataclass(frozen=True)
class TransactionSummary:
    total_transactions: int
    total_income: float
    income_count: int
    total_expenses: float
    expense_count: int
    net_cash_flow: float
    top_categories: list[dict[str, float]] = field(default_factory=list)


@dataclass(frozen=True)
class BudgetSummary:
    total_budgets: int
    budgets: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class TaxSummary:
    latest_calculation: dict | None = None
    total_calculations: int = 0


@dataclass(frozen=True)
class FullFinancialContext:
    """Complete verified financial context for the authenticated user."""
    user_name: str
    transactions: TransactionSummary
    budgets: BudgetSummary
    tax: TaxSummary


def get_transaction_summary(session: Session, user_id: UUID) -> TransactionSummary:
    """Gather deterministic transaction summary from DB."""
    total_transactions = session.scalar(
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    ) or 0

    total_income_result = session.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
        )
    ).one()
    total_income = float(total_income_result[0])
    income_count = total_income_result[1]

    total_expense_result = session.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
        )
    ).one()
    total_expenses = float(total_expense_result[0])
    expense_count = total_expense_result[1]

    top_categories = session.execute(
        select(
            TransactionCategory.name,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(TransactionCategory, Transaction.category_id == TransactionCategory.id)
        .where(Transaction.user_id == user_id)
        .group_by(TransactionCategory.name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    ).all()

    return TransactionSummary(
        total_transactions=total_transactions,
        total_income=total_income,
        income_count=income_count,
        total_expenses=total_expenses,
        expense_count=expense_count,
        net_cash_flow=total_income - total_expenses,
        top_categories=[{"name": name, "total": float(total)} for name, total in top_categories],
    )


def get_budget_summary(session: Session, user_id: UUID) -> BudgetSummary:
    """Gather deterministic budget summary from DB."""
    from app.db.repositories.budget_repository import BudgetRepository

    repository = BudgetRepository(session)
    budgets = repository.list_budgets_for_user(user_id)
    budget_data = []
    for b in budgets:
        spending, tx_count = repository.get_spending_for_budget(
            user_id=user_id,
            category_id=b.category_id,
            period_start=b.period_start,
            period_end=b.period_end,
        )
        category_name = repository.get_category_name(b.category_id) or "Unknown"
        budget_amount = float(b.budget_amount)
        percentage = float(spending / b.budget_amount) if b.budget_amount > 0 else 0.0
        if percentage < 0.80:
            status = "under_budget"
        elif percentage <= 1.00:
            status = "near_limit"
        else:
            status = "over_budget"
        budget_data.append({
            "category": category_name,
            "budget_amount": budget_amount,
            "actual_spending": float(spending),
            "percentage_used": percentage,
            "status": status,
            "period_start": str(b.period_start),
            "period_end": str(b.period_end),
        })
    return BudgetSummary(total_budgets=len(budgets), budgets=budget_data)


def get_tax_summary(session: Session, user_id: UUID) -> TaxSummary:
    """Gather deterministic tax summary from DB."""
    from app.db.repositories.tax_calculation_repository import TaxCalculationRepository

    repository = TaxCalculationRepository(session)
    calculations = repository.list_for_user(user_id)
    latest = None
    if calculations:
        calc = calculations[0]
        latest = {
            "tax_year": calc.tax_year,
            "total_income": float(calc.total_income),
            "total_allowances": float(calc.total_allowances),
            "taxable_income": float(calc.taxable_income),
            "income_tax_due": float(calc.income_tax_due),
            "rules_version": calc.rules_version,
        }
    return TaxSummary(latest_calculation=latest, total_calculations=len(calculations))


def get_full_financial_context(
    session: Session,
    user_id: UUID,
    user_name: str,
) -> FullFinancialContext:
    """Aggregate all verified financial data for the authenticated user."""
    return FullFinancialContext(
        user_name=user_name,
        transactions=get_transaction_summary(session, user_id),
        budgets=get_budget_summary(session, user_id),
        tax=get_tax_summary(session, user_id),
    )
