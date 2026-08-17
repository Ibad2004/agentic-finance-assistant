import pytest

from app.services.merchant_categorization_rules import match_merchant_rule


@pytest.mark.parametrize(("description", "transaction_type", "category"), [
    ("  TESCO   STORES ", "expense", "Food"),
    ("TfL TRAVEL CHARGE", "expense", "Transport"),
    ("NETFLIX.COM", "expense", "Subscriptions"),
    ("ACME PAYROLL LTD", "income", "Salary"),
])
def test_clear_rules_categorize_expected_merchants(description: str, transaction_type: str, category: str) -> None:
    result = match_merchant_rule(description, transaction_type)
    assert result is not None
    assert result.category_name == category
    assert result.confidence == 1.0


def test_payroll_expense_is_not_salary() -> None:
    assert match_merchant_rule("PAYROLL ADJUSTMENT", "expense") is None


def test_unknown_merchant_has_no_deterministic_match() -> None:
    assert match_merchant_rule("CARD PAYMENT XYZ", "expense") is None
