from decimal import Decimal

import pytest

from app.services.csv_parser import parse_normalized_csv


HEADER = "transaction_date,description,debit,credit,balance,reference,currency\n"


def parse_row(row: str):
    return parse_normalized_csv((HEADER + row + "\n").encode())


def issue_codes(result) -> set[str]:
    return {issue.code for issue in result.validation_errors}


def test_valid_income_row_is_parsed_with_positive_amount() -> None:
    result = parse_row("2026-04-06,ACME PAYROLL LTD,,2850.00,2850.00,SALARY-APR,GBP")

    assert result.rows_read == 1
    assert not result.validation_errors
    row = result.valid_rows[0]
    assert row.amount == Decimal("2850.00")
    assert row.transaction_type == "income"
    assert row.balance == Decimal("2850.00")


def test_valid_expense_row_is_parsed_with_positive_amount() -> None:
    result = parse_row("2026-04-07,TESCO STORES,63.28,,2786.72,TESCO-0407,GBP")

    row = result.valid_rows[0]
    assert row.amount == Decimal("63.28")
    assert row.transaction_type == "expense"


def test_invalid_date_is_rejected() -> None:
    result = parse_row("07/04/2026,TESCO STORES,63.28,,,GBP")

    assert not result.valid_rows
    assert "invalid_date" in issue_codes(result)


@pytest.mark.parametrize("value", ["abc", "10.999", "0", "0.00"])
def test_invalid_amount_is_rejected(value: str) -> None:
    result = parse_row(f"2026-04-07,TESCO STORES,{value},,,GBP")

    assert not result.valid_rows
    assert "invalid_amount" in issue_codes(result)


@pytest.mark.parametrize("value", ["-10", "-10.00"])
def test_negative_debit_or_credit_is_rejected(value: str) -> None:
    debit_result = parse_row(f"2026-04-07,TESCO STORES,{value},,,GBP")
    credit_result = parse_row(f"2026-04-07,ACME PAYROLL,,{value},,GBP")

    assert "invalid_amount" in issue_codes(debit_result)
    assert "invalid_amount" in issue_codes(credit_result)


def test_both_debit_and_credit_are_rejected() -> None:
    result = parse_row("2026-04-07,AMBIGUOUS,10.00,5.00,,REF,GBP")

    assert "both_debit_and_credit" in issue_codes(result)


def test_neither_debit_nor_credit_is_rejected() -> None:
    result = parse_row("2026-04-07,NO VALUE,,,,GBP")

    assert "missing_debit_and_credit" in issue_codes(result)


def test_invalid_currency_is_rejected() -> None:
    result = parse_row("2026-04-07,FOREIGN PAYMENT,10.00,,,USD")

    assert "invalid_currency" in issue_codes(result)


def test_missing_required_columns_are_rejected() -> None:
    result = parse_normalized_csv(b"transaction_date,description,debit\n2026-04-07,TESCO,10.00\n")

    assert "missing_required_columns" in issue_codes(result)


def test_non_utf8_csv_is_rejected() -> None:
    result = parse_normalized_csv(b"\xff\xfeinvalid")

    assert "invalid_encoding" in issue_codes(result)


def test_row_with_more_values_than_headers_is_rejected() -> None:
    result = parse_row("2026-04-07,TESCO,10.00,,,,GBP,unexpected")

    assert "malformed_row" in issue_codes(result)


def test_empty_description_is_rejected() -> None:
    result = parse_row("2026-04-07,   ,10.00,,,GBP")

    assert "empty_description" in issue_codes(result)


def test_invalid_balance_is_rejected_without_becoming_an_amount() -> None:
    result = parse_row("2026-04-07,TESCO,10.00,,not-a-number,REF,GBP")

    assert "invalid_balance" in issue_codes(result)
