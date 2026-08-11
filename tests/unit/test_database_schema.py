from sqlalchemy import ForeignKeyConstraint, Numeric

from app.db.base import Base
from app.db.models import Transaction, TaxCalculation


def test_mvp_schema_contains_only_approved_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "financial_accounts",
        "transaction_categories",
        "transactions",
        "budgets",
        "tax_calculations",
        "financial_reports",
        "audit_logs",
    }


def test_financial_amounts_use_fixed_precision_numeric() -> None:
    for column in (
        Transaction.__table__.c.amount,
        TaxCalculation.__table__.c.total_income,
        TaxCalculation.__table__.c.total_allowances,
        TaxCalculation.__table__.c.taxable_income,
        TaxCalculation.__table__.c.income_tax_due,
    ):
        assert isinstance(column.type, Numeric)
        assert (column.type.precision, column.type.scale) == (18, 2)


def test_transactions_require_an_account_owned_by_the_same_user() -> None:
    composite_foreign_key = next(
        constraint
        for constraint in Transaction.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == "fk_transactions_account_id_user_id_financial_accounts"
    )

    assert [element.parent.name for element in composite_foreign_key.elements] == ["account_id", "user_id"]
    assert [element.column.name for element in composite_foreign_key.elements] == ["id", "user_id"]
