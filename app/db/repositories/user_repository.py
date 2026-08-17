"""Repository for User database operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        return self._session.scalar(
            select(User).where(func.lower(User.email) == email.strip().lower())
        )

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._session.scalar(
            select(User).where(User.id == user_id)
        )

    def create_user(self, email: str, password_hash: str, full_name: str | None = None) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name.strip() if full_name else None,
            is_active=True,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
