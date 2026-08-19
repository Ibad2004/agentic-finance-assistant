"""Category listing endpoint for frontend budget creation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.db.models import TransactionCategory, User
from app.schemas.transaction_categorization import CategorySummary

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=list[CategorySummary],
    status_code=200,
    summary="List all active transaction categories",
)
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CategorySummary]:
    """Return all active seeded transaction categories.

    Categories are global and shared across all users.
    They are seeded by ``scripts/seed_categories.py`` and are read-only for the frontend.
    """
    categories = db.scalars(
        select(TransactionCategory)
        .where(TransactionCategory.is_active.is_(True))
        .order_by(TransactionCategory.name)
    )
    return [
        CategorySummary(id=c.id, name=c.name, category_type=c.category_type)
        for c in categories
    ]
