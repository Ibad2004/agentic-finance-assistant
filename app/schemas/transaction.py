"""Pydantic schemas for safe financial transaction responses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransactionResponse(BaseModel):
    id: UUID
    transaction_date: date
    description: str
    amount: Decimal
    transaction_type: str
    category: str | None = None
    source: str
    is_reviewed: bool

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total_count: int
