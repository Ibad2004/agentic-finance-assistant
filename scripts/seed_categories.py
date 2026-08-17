"""Seed the 15 approved transaction categories into PostgreSQL idempotently."""

from __future__ import annotations

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TransactionCategory
from app.db.session import SessionLocal

APPROVED_CATEGORIES: Sequence[tuple[str, str]] = (
    ("Salary", "income"),
    ("Freelance Income", "income"),
    ("Other Income", "income"),
    ("Housing", "expense"),
    ("Food", "expense"),
    ("Transport", "expense"),
    ("Utilities", "expense"),
    ("Healthcare", "expense"),
    ("Shopping", "expense"),
    ("Entertainment", "expense"),
    ("Subscriptions", "expense"),
    ("Education", "expense"),
    ("Insurance", "expense"),
    ("Personal Care", "expense"),
    ("Other Expense", "expense"),
)


def seed_categories(session: Session) -> dict[str, int]:
    """Insert missing approved categories without creating duplicates."""
    existing_categories = list(session.scalars(select(TransactionCategory)))
    existing_map = {(cat.name, cat.category_type): cat for cat in existing_categories}

    inserted_count = 0
    for name, category_type in APPROVED_CATEGORIES:
        if (name, category_type) not in existing_map:
            new_cat = TransactionCategory(
                name=name,
                category_type=category_type,
                is_active=True,
            )
            session.add(new_cat)
            inserted_count += 1
        else:
            cat = existing_map[(name, category_type)]
            if not cat.is_active:
                cat.is_active = True

    session.commit()

    total_categories = len(list(session.scalars(select(TransactionCategory))))
    return {
        "inserted": inserted_count,
        "existing": len(existing_categories),
        "total": total_categories,
    }


def main() -> None:
    session = SessionLocal()
    try:
        stats = seed_categories(session)
        print(f"Seeding complete: {stats['inserted']} inserted, {stats['existing']} existed, {stats['total']} total active categories in database.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
