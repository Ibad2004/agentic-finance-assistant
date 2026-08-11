"""SQLAlchemy ORM models for the approved MVP schema."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    and_,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """A registered application user; password_hash never stores a raw password."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    accounts: Mapped[list[FinancialAccount]] = relationship(back_populates="user")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="user", foreign_keys="Transaction.user_id")
    budgets: Mapped[list[Budget]] = relationship(back_populates="user")
    tax_calculations: Mapped[list[TaxCalculation]] = relationship(back_populates="user")
    financial_reports: Mapped[list[FinancialReport]] = relationship(back_populates="user")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")


Index("ix_users_email_lower", func.lower(User.email), unique=True)


class FinancialAccount(Base):
    """A user-owned financial account represented by CSV or sample data in the MVP."""

    __tablename__ = "financial_accounts"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_financial_accounts_id_user_id"),
        CheckConstraint(
            "account_type IN ('current', 'savings', 'credit_card', 'cash')",
            name="ck_financial_accounts_account_type",
        ),
        CheckConstraint("currency_code = 'GBP'", name="ck_financial_accounts_currency_code"),
        Index("ix_financial_accounts_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False, default="GBP", server_default="GBP")
    current_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    balance_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="accounts")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="account",
        primaryjoin=lambda: and_(
            FinancialAccount.id == Transaction.account_id,
            FinancialAccount.user_id == Transaction.user_id,
        ),
        foreign_keys=lambda: [Transaction.account_id, Transaction.user_id],
        overlaps="user,transactions",
    )


class TransactionCategory(Base):
    """Reusable global category for income or expense transactions."""

    __tablename__ = "transaction_categories"
    __table_args__ = (
        UniqueConstraint("name", "category_type", name="uq_transaction_categories_name_type"),
        CheckConstraint("category_type IN ('income', 'expense')", name="ck_transaction_categories_category_type"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_type: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    transactions: Mapped[list[Transaction]] = relationship(back_populates="category")
    budgets: Mapped[list[Budget]] = relationship(back_populates="category")


class Transaction(Base):
    """A user-owned ledger entry with a positive amount and explicit direction."""

    __tablename__ = "transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["financial_accounts.id", "financial_accounts.user_id"],
            name="fk_transactions_account_id_user_id_financial_accounts",
        ),
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        CheckConstraint("transaction_type IN ('income', 'expense')", name="ck_transactions_transaction_type"),
        CheckConstraint("source IN ('csv', 'sample')", name="ck_transactions_source"),
        CheckConstraint("length(trim(description)) > 0", name="ck_transactions_description_not_blank"),
        Index("ix_transactions_user_transaction_date", "user_id", "transaction_date"),
        Index("ix_transactions_account_transaction_date", "account_id", "transaction_date"),
        Index("ix_transactions_category_id", "category_id"),
        UniqueConstraint("account_id", "source_reference", name="uq_transactions_account_source_reference"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("transaction_categories.id"), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="transactions", foreign_keys=[user_id])
    account: Mapped[FinancialAccount] = relationship(
        back_populates="transactions",
        primaryjoin=lambda: and_(
            Transaction.account_id == FinancialAccount.id,
            Transaction.user_id == FinancialAccount.user_id,
        ),
        foreign_keys=[account_id, user_id],
        overlaps="user,transactions",
    )
    category: Mapped[TransactionCategory | None] = relationship(back_populates="transactions")


class Budget(Base):
    """A category spending limit for a user-defined date range."""

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "period_start", "period_end", name="uq_budgets_user_category_period"),
        CheckConstraint("budget_amount >= 0", name="ck_budgets_amount_non_negative"),
        CheckConstraint("period_end >= period_start", name="ck_budgets_period_valid"),
        Index("ix_budgets_user_period", "user_id", "period_start", "period_end"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("transaction_categories.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="budgets")
    category: Mapped[TransactionCategory] = relationship(back_populates="budgets")


class TaxCalculation(Base):
    """A deterministic England Income Tax estimate and its tax-rule version."""

    __tablename__ = "tax_calculations"
    __table_args__ = (
        CheckConstraint("tax_year = '2026/27'", name="ck_tax_calculations_tax_year"),
        CheckConstraint("total_income >= 0", name="ck_tax_calculations_total_income_non_negative"),
        CheckConstraint("total_allowances >= 0", name="ck_tax_calculations_allowances_non_negative"),
        CheckConstraint("taxable_income >= 0", name="ck_tax_calculations_taxable_income_non_negative"),
        CheckConstraint("income_tax_due >= 0", name="ck_tax_calculations_income_tax_due_non_negative"),
        Index("ix_tax_calculations_user_tax_year", "user_id", "tax_year"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    tax_year: Mapped[str] = mapped_column(String(7), nullable=False)
    rules_version: Mapped[str] = mapped_column(String(50), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    total_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_allowances: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    taxable_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    income_tax_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    assumptions: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    calculation_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    user: Mapped[User] = relationship(back_populates="tax_calculations")
    financial_reports: Mapped[list[FinancialReport]] = relationship(back_populates="tax_calculation")


class FinancialReport(Base):
    """Metadata for a PDF or Excel report generated from validated data."""

    __tablename__ = "financial_reports"
    __table_args__ = (
        CheckConstraint("period_end >= period_start", name="ck_financial_reports_period_valid"),
        CheckConstraint("file_format IN ('pdf', 'xlsx')", name="ck_financial_reports_file_format"),
        CheckConstraint(
            "report_type IN ('monthly_summary', 'expense_summary', 'tax_summary')",
            name="ck_financial_reports_report_type",
        ),
        Index("ix_financial_reports_user_generated_at", "user_id", "generated_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    tax_calculation_id: Mapped[UUID | None] = mapped_column(ForeignKey("tax_calculations.id"), nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="financial_reports")
    tax_calculation: Mapped[TaxCalculation | None] = relationship(back_populates="financial_reports")


class AuditLog(Base):
    """Insert-only application audit record for sensitive actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_created_at", "user_id", "created_at"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="audit_logs")
