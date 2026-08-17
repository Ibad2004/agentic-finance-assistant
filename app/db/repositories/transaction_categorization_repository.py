"""Controlled database access for Transaction Agent categorization."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Transaction, TransactionCategory
from app.schemas.transaction_categorization import CategoryAssignment, CategorySummary, TransactionForCategorization


class TransactionCategorizationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_approved_categories(self) -> list[CategorySummary]:
        categories = self._session.scalars(select(TransactionCategory).where(TransactionCategory.is_active.is_(True)).order_by(TransactionCategory.name))
        return [CategorySummary(id=c.id, name=c.name, category_type=c.category_type) for c in categories]

    def get_uncategorized_batch(self, user_id: UUID, limit: int, excluded_ids: set[UUID]) -> list[TransactionForCategorization]:
        statement = select(Transaction).where(Transaction.user_id == user_id, Transaction.category_id.is_(None))
        if excluded_ids:
            statement = statement.where(Transaction.id.not_in(excluded_ids))
        transactions = self._session.scalars(statement.order_by(Transaction.transaction_date, Transaction.id).limit(limit))
        return [TransactionForCategorization(id=t.id, description=t.description, transaction_type=t.transaction_type, amount=t.amount) for t in transactions]

    def save_category_assignments(self, user_id: UUID, assignments: list[CategoryAssignment], categories: dict[UUID, CategorySummary]) -> list[UUID]:
        saved: list[UUID] = []
        for assignment in assignments:
            transaction = self._session.scalar(select(Transaction).where(Transaction.id == assignment.transaction_id, Transaction.user_id == user_id, Transaction.category_id.is_(None)))
            category = categories.get(assignment.category_id)
            if transaction is None or category is None or transaction.transaction_type != category.category_type:
                continue
            transaction.category_id = assignment.category_id
            saved.append(transaction.id)
        self._session.flush()
        return saved

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    @property
    def session(self) -> Session:
        return self._session
