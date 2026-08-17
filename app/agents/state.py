"""LangGraph state for the single MVP Transaction Agent."""

from typing import Any, TypedDict
from uuid import UUID

from app.schemas.transaction_categorization import CategorySummary, TransactionForCategorization
from app.schemas.transaction_categorization import CategoryAssignment


class TransactionCategorizationState(TypedDict, total=False):
    user_id: UUID
    batch_size: int
    confidence_threshold: float
    batch_cursor: int
    batches_processed: int
    approved_categories: list[CategorySummary]
    current_batch: list[TransactionForCategorization]
    deterministic_matches: dict[UUID, str]
    llm_transactions: list[TransactionForCategorization]
    llm_batch_response: Any
    validated_assignments: list[CategoryAssignment]
    saved_transaction_ids: list[UUID]
    needs_review_transactions: list[UUID]
    failed_transactions: list[dict[str, Any]]
    sanitized_errors: list[str]
    processed_transaction_ids: set[UUID]
