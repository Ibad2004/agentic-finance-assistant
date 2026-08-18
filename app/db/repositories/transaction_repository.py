"""Controlled SQLAlchemy access for accounts and CSV-imported transactions."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import FinancialAccount, Transaction


class TransactionRepository:
    """Database operations used by the CSV import service and transaction queries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_account_for_user(self, account_id: UUID, user_id: UUID) -> FinancialAccount | None:
        return self._session.scalar(
            select(FinancialAccount).where(
                FinancialAccount.id == account_id,
                FinancialAccount.user_id == user_id,
            )
        )

    def find_transactions_by_source_references(
        self, account_id: UUID, source_references: set[str]
    ) -> list[Transaction]:
        if not source_references:
            return []
        return list(
            self._session.scalars(
                select(Transaction).where(
                    Transaction.account_id == account_id,
                    Transaction.source_reference.in_(source_references),
                )
            )
        )

    def find_fingerprint_candidates(
        self,
        account_id: UUID,
        transaction_date: date,
        amount: Decimal,
        transaction_type: str,
    ) -> list[Transaction]:
        return list(
            self._session.scalars(
                select(Transaction).where(
                    Transaction.account_id == account_id,
                    Transaction.transaction_date == transaction_date,
                    Transaction.amount == amount,
                    Transaction.transaction_type == transaction_type,
                )
            )
        )

    def add_transactions(self, transactions: list[Transaction]) -> None:
        self._session.add_all(transactions)
        self._session.flush()

    def update_account_balance(
        self, account: FinancialAccount, balance: Decimal, updated_at: datetime
    ) -> None:
        account.current_balance = balance
        account.balance_updated_at = updated_at

    def list_transactions_for_account(
        self,
        account_id: UUID,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
        start_date: date | None = None,
        end_date: date | None = None,
        category_id: UUID | None = None,
        transaction_type: str | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
    ) -> tuple[list[Transaction], int]:
        base_filter = [
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
        ]
        if start_date is not None:
            base_filter.append(Transaction.transaction_date >= start_date)
        if end_date is not None:
            base_filter.append(Transaction.transaction_date <= end_date)
        if category_id is not None:
            base_filter.append(Transaction.category_id == category_id)
        if transaction_type is not None:
            base_filter.append(Transaction.transaction_type == transaction_type)
        if min_amount is not None:
            base_filter.append(Transaction.amount >= min_amount)
        if max_amount is not None:
            base_filter.append(Transaction.amount <= max_amount)

        total = self._session.scalar(
            select(func.count(Transaction.id)).where(*base_filter)
        ) or 0

        transactions = list(
            self._session.scalars(
                select(Transaction)
                .options(joinedload(Transaction.category))
                .where(*base_filter)
                .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return transactions, total

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

