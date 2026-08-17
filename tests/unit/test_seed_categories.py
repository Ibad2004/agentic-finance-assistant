from __future__ import annotations

from unittest.mock import MagicMock
from app.db.models import TransactionCategory
from scripts.seed_categories import APPROVED_CATEGORIES, seed_categories


class FakeCategorySession:
    def __init__(self, existing: list[TransactionCategory] | None = None) -> None:
        self.categories: list[TransactionCategory] = list(existing or [])
        self.added: list[TransactionCategory] = []
        self.committed = False

    def scalars(self, statement):
        # Return currently stored and added categories
        all_cats = self.categories + self.added
        return all_cats

    def add(self, instance: TransactionCategory) -> None:
        self.added.append(instance)

    def commit(self) -> None:
        self.committed = True


def test_seed_categories_seeds_all_when_empty() -> None:
    session = FakeCategorySession()
    stats = seed_categories(session)  # type: ignore[arg-type]

    assert stats["inserted"] == 15
    assert stats["existing"] == 0
    assert stats["total"] == 15
    assert session.committed is True
    assert len(session.added) == 15
    names = {cat.name for cat in session.added}
    assert "Salary" in names
    assert "Food" in names


def test_seed_categories_is_idempotent() -> None:
    existing = [
        TransactionCategory(name=name, category_type=ctype, is_active=True)
        for name, ctype in APPROVED_CATEGORIES
    ]
    session = FakeCategorySession(existing=existing)
    stats = seed_categories(session)  # type: ignore[arg-type]

    assert stats["inserted"] == 0
    assert stats["existing"] == 15
    assert stats["total"] == 15
    assert len(session.added) == 0
