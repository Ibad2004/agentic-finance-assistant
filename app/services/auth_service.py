"""Application service for user authentication, registration, and token generation."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.db.models import User
from app.db.repositories.user_repository import UserRepository
from app.security.jwt import create_access_token
from app.security.password import hash_password, verify_password


class EmailAlreadyExistsError(Exception):
    """Raised when an account already exists with the given email address."""


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def register_user(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        normalized_email = email.strip().lower()
        existing = self._repository.get_by_email(normalized_email)
        if existing is not None:
            raise EmailAlreadyExistsError("An account with this email address already exists.")

        hashed_pw = hash_password(password)
        user = self._repository.create_user(
            email=normalized_email,
            password_hash=hashed_pw,
            full_name=full_name,
        )
        self._repository.commit()
        return user

    def authenticate_user(self, email: str, password: str) -> User | None:
        normalized_email = email.strip().lower()
        user = self._repository.get_by_email(normalized_email)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_user_token(
        self,
        user_id: UUID,
        secret_key: str,
        expire_minutes: int = 1440,
        algorithm: str = "HS256",
    ) -> str:
        return create_access_token(
            user_id=user_id,
            secret_key=secret_key,
            expires_delta=timedelta(minutes=expire_minutes),
            algorithm=algorithm,
        )
