"""Unit tests for the TaxAgent."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.agents.tax_agent import TaxAgent
from app.db.models import TaxCalculation


class MockSession:
    """Mock SQLAlchemy session for testing."""
    def __init__(self) -> None:
        self.added: list[TaxCalculation] = []
        self.committed = False

    def add(self, instance: TaxCalculation) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


def test_tax_agent_calculate_and_save() -> None:
    """Test that the TaxAgent correctly calculates and persists a tax calculation."""
    session = MockSession()
    agent = TaxAgent(session)
    user_id = uuid4()
    total_income = Decimal("50000.00")
    # No custom allowance -> use standard Personal Allowance
    tax_calculation = agent.calculate_and_save(
        user_id=user_id,
        total_income=total_income,
        custom_allowance=None,
    )

    assert isinstance(tax_calculation, TaxCalculation)
    assert tax_calculation.user_id == user_id
    assert tax_calculation.total_income == total_income
    # For income 50000, personal allowance 12570, taxable income 37430
    # Tax: 37430 * 0.2 = 7486.00
    assert tax_calculation.income_tax_due == Decimal("7486.00")
    assert session.committed is True


def test_tax_agent_custom_allowance() -> None:
    """Test TaxAgent with a custom allowance."""
    session = MockSession()
    agent = TaxAgent(session)
    user_id = uuid4()
    total_income = Decimal("30000.00")
    custom_allowance = Decimal("15000.00")

    tax_calculation = agent.calculate_and_save(
        user_id=user_id,
        total_income=total_income,
        custom_allowance=custom_allowance,
    )

    assert tax_calculation.total_allowances == custom_allowance
    # Taxable income = 30000 - 15000 = 15000
    # Tax = 15000 * 0.2 = 3000.00
    assert tax_calculation.income_tax_due == Decimal("3000.00")