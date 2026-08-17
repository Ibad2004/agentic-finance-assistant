"""Authentication endpoints for user registration and login."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.config import Settings, get_settings
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService, EmailAlreadyExistsError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    payload: UserRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Register a new user account. Passwords are safe-hashed; password_hash is never returned."""
    service = AuthService(UserRepository(db))
    try:
        user = service.register_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
        return UserResponse.model_validate(user)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT token",
)
def login(
    payload: UserLoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Authenticate with email and password to receive a signed JWT Bearer access token."""
    service = AuthService(UserRepository(db))
    user = service.authenticate_user(email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = service.create_user_token(
        user_id=user.id,
        secret_key=settings.jwt_secret_key.get_secret_value(),
        expire_minutes=settings.jwt_access_token_expire_minutes,
        algorithm=settings.jwt_algorithm,
    )
    return TokenResponse(access_token=token, token_type="bearer")
