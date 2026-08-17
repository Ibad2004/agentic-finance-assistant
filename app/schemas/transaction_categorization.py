"""Safe data contracts for Transaction Agent categorization."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CategorySummary(BaseModel):
    id: UUID
    name: str
    category_type: str


class TransactionForCategorization(BaseModel):
    id: UUID
    description: str
    transaction_type: str
    amount: Decimal


class LlmCategorizationResult(BaseModel):
    transaction_id: UUID
    category_name: str
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must not be blank")
        return value


class LlmBatchCategorizationResponse(BaseModel):
    results: list[LlmCategorizationResult]


class CategoryAssignment(BaseModel):
    transaction_id: UUID
    category_id: UUID


class CategorizationFailure(BaseModel):
    transaction_id: UUID | None = None
    code: str


class CategorizationRunResult(BaseModel):
    saved_transaction_ids: list[UUID] = Field(default_factory=list)
    needs_review_transaction_ids: list[UUID] = Field(default_factory=list)
    failed_transactions: list[CategorizationFailure] = Field(default_factory=list)
    sanitized_errors: list[str] = Field(default_factory=list)
    batches_processed: int = 0


JsonObject = dict[str, Any]
