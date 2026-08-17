"""Deterministic validation for Transaction Agent LLM batch results."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.schemas.transaction_categorization import (
    CategoryAssignment,
    CategorySummary,
    LlmBatchCategorizationResponse,
    TransactionForCategorization,
)


APPROVED_CATEGORY_NAMES = frozenset({
    "Salary", "Freelance Income", "Other Income", "Housing", "Food", "Transport", "Utilities",
    "Healthcare", "Shopping", "Entertainment", "Subscriptions", "Education", "Insurance",
    "Personal Care", "Other Expense",
})


def approved_categories_only(categories: list[CategorySummary]) -> list[CategorySummary]:
    return [category for category in categories if category.name in APPROVED_CATEGORY_NAMES]


def validate_llm_batch_response(
    response: Any,
    current_batch: list[TransactionForCategorization],
    categories: list[CategorySummary],
    confidence_threshold: float,
) -> tuple[list[CategoryAssignment], list[UUID], list[dict[str, str]]]:
    """Validate every response item before any category write is attempted."""

    batch_by_id = {transaction.id: transaction for transaction in current_batch}
    category_by_name = {category.name: category for category in categories}
    try:
        parsed = response if isinstance(response, LlmBatchCategorizationResponse) else LlmBatchCategorizationResponse.model_validate(response)
    except ValidationError:
        return [], [], [{"code": "invalid_llm_response"}]

    assignments: list[CategoryAssignment] = []
    needs_review: list[UUID] = []
    failures: list[dict[str, str]] = []
    seen_ids: set[UUID] = set()
    returned_ids: set[UUID] = set()
    for item in parsed.results:
        if item.transaction_id not in batch_by_id:
            failures.append({"code": "unexpected_transaction_id"})
            continue
        if item.transaction_id in seen_ids:
            failures.append({"code": "duplicate_transaction_id"})
            continue
        seen_ids.add(item.transaction_id)
        returned_ids.add(item.transaction_id)
        category = category_by_name.get(item.category_name)
        if category is None:
            failures.append({"code": "invalid_category"})
            continue
        if category.category_type != batch_by_id[item.transaction_id].transaction_type:
            failures.append({"code": "wrong_category_type"})
            continue
        if item.confidence < confidence_threshold:
            needs_review.append(item.transaction_id)
            continue
        assignments.append(CategoryAssignment(transaction_id=item.transaction_id, category_id=category.id))

    for transaction in current_batch:
        if transaction.id not in returned_ids:
            failures.append({"code": "missing_result"})
    return assignments, needs_review, failures
