"""Provider-neutral interface for transaction categorization LLMs."""

from typing import Protocol

from app.schemas.transaction_categorization import (
    CategorySummary,
    LlmBatchCategorizationResponse,
    TransactionForCategorization,
)


class TransactionCategorizationLlm(Protocol):
    def categorize_batch(
        self,
        transactions: list[TransactionForCategorization],
        approved_categories: list[CategorySummary],
    ) -> LlmBatchCategorizationResponse: ...
