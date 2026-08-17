"""Repository for FinancialAccount database operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FinancialAccount


class AccountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_account(
        self,
        user_id: UUID,
        account_name: str,
        account_type: str,
        currency_code: str = "GBP",
    ) -> FinancialAccount:
        account = FinancialAccount(
            user_id=user_id,
            account_name=account_name.strip(),
            account_type=account_type,
            currency_code=currency_code,
            is_active=True,
        )
        self._session.add(account)
        self._session.flush()
        return account

    def get_account_for_user(self, account_id: UUID, user_id: UUID) -> FinancialAccount | None:
        return self._session.scalar(
            select(FinancialAccount).where(
                FinancialAccount.id == account_id,
                FinancialAccount.user_id == user_id,
            )
        )

    def list_accounts_for_user(self, user_id: UUID) -> list[FinancialAccount]:
        return list(
            self._session.scalars(
                select(FinancialAccount)
                .where(FinancialAccount.user_id == user_id)
                .order_by(FinancialAccount.created_at.asc())
            )
        )

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
