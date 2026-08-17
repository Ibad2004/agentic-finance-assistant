"""Groq adapter for the provider-neutral Transaction Agent LLM interface."""

import json

from langchain_groq import ChatGroq

from app.config import Settings
from app.schemas.transaction_categorization import (
    CategorySummary,
    LlmBatchCategorizationResponse,
    TransactionForCategorization,
)


class GroqTransactionCategorizationLlm:
    """Calls Groq with structured output and only minimal categorization data."""

    def __init__(self, settings: Settings) -> None:
        if settings.groq_api_key is None:
            raise RuntimeError("Groq is not configured.")
        self._model = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key.get_secret_value(),
            temperature=0,
        ).with_structured_output(LlmBatchCategorizationResponse)

    def categorize_batch(
        self,
        transactions: list[TransactionForCategorization],
        approved_categories: list[CategorySummary],
    ) -> LlmBatchCategorizationResponse:
        prompt = {
            "task": "Categorize each transaction using exactly one approved category, or return low confidence when uncertain.",
            "approved_categories": [
                {"name": category.name, "category_type": category.category_type}
                for category in approved_categories
            ],
            "transactions": [
                {
                    "transaction_id": str(transaction.id),
                    "description": transaction.description,
                    "transaction_type": transaction.transaction_type,
                }
                for transaction in transactions
            ],
        }
        return self._model.invoke(json.dumps(prompt))

