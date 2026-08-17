"""Pydantic schemas for authentication and user accounts."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=150)

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if not _EMAIL_REGEX.fullmatch(trimmed):
            raise ValueError("Invalid email address format.")
        return trimmed


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if not _EMAIL_REGEX.fullmatch(trimmed):
            raise ValueError("Invalid email address format.")
        return trimmed



class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
