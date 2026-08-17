"""Pydantic schemas for user financial accounts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AccountType = Literal["current", "savings", "credit_card", "cash"]


class AccountCreateRequest(BaseModel):
    account_name: str = Field(min_length=1, max_length=150)
    account_type: AccountType
    currency_code: str = Field(default="GBP")

    @field_validator("account_name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("account_name cannot be blank.")
        return trimmed

    @field_validator("currency_code")
    @classmethod
    def currency_must_be_gbp(cls, value: str) -> str:
        if value.strip().upper() != "GBP":
            raise ValueError("Only GBP currency is supported in the MVP.")
        return "GBP"


class AccountResponse(BaseModel):
    id: UUID
    account_name: str
    account_type: str
    currency_code: str
    current_balance: Decimal | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
