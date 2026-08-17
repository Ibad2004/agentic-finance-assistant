"""Application service for user-owned financial accounts."""

from __future__ import annotations

from uuid import UUID

from app.db.models import FinancialAccount
from app.db.repositories.account_repository import AccountRepository


class AccountService:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    def create_account(
        self,
        user_id: UUID,
        account_name: str,
        account_type: str,
        currency_code: str = "GBP",
    ) -> FinancialAccount:
        account = self._repository.create_account(
            user_id=user_id,
            account_name=account_name,
            account_type=account_type,
            currency_code=currency_code,
        )
        self._repository.commit()
        return account

    def get_account_for_user(self, account_id: UUID, user_id: UUID) -> FinancialAccount | None:
        return self._repository.get_account_for_user(account_id=account_id, user_id=user_id)

    def list_accounts_for_user(self, user_id: UUID) -> list[FinancialAccount]:
        return self._repository.list_accounts_for_user(user_id=user_id)
