"""Controlled tools used by the Transaction Agent graph."""

from uuid import UUID

from app.db.repositories.transaction_categorization_repository import TransactionCategorizationRepository
from app.schemas.transaction_categorization import CategoryAssignment, CategorySummary, TransactionForCategorization
from app.services.audit_service import record_audit_log


class TransactionCategorizationTools:
    def __init__(self, repository: TransactionCategorizationRepository) -> None:
        self._repository = repository

    def get_uncategorized_transaction_batch(self, user_id: UUID, limit: int, excluded_ids: set[UUID]) -> list[TransactionForCategorization]:
        return self._repository.get_uncategorized_batch(user_id, limit, excluded_ids)

    def get_approved_categories(self) -> list[CategorySummary]:
        return self._repository.get_approved_categories()

    def save_category_assignments(self, user_id: UUID, assignments: list[CategoryAssignment], categories: dict[UUID, CategorySummary]) -> list[UUID]:
        return self._repository.save_category_assignments(user_id, assignments, categories)

    def record_categorization_event(self, user_id: UUID, transaction_id: UUID | None, action_type: str, code: str) -> None:
        record_audit_log(self._repository.session, user_id=user_id, action_type=action_type, entity_type="transaction", entity_id=transaction_id, metadata={"code": code})

    def commit(self) -> None:
        self._repository.commit()

    def rollback(self) -> None:
        self._repository.rollback()
