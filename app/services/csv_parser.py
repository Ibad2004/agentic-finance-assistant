"""Parsing and validation for the normalized UK-bank-style CSV format."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO

from app.schemas.csv_import import ImportIssue


REQUIRED_COLUMNS = {"transaction_date", "description", "debit", "credit", "currency"}
OPTIONAL_COLUMNS = {"balance", "reference"}
_AMOUNT_PATTERN = re.compile(r"^\d+(?:\.\d{1,2})?$")
_BALANCE_PATTERN = re.compile(r"^-?\d+(?:\.\d{1,2})?$")


@dataclass(frozen=True)
class ParsedTransactionRow:
    """A valid, normalized transaction row ready for duplicate checks and persistence."""

    row_number: int
    transaction_date: date
    description: str
    amount: Decimal
    transaction_type: str
    balance: Decimal | None
    reference: str | None


@dataclass
class CsvParseResult:
    """Parser output kept separate from database persistence."""

    rows_read: int = 0
    valid_rows: list[ParsedTransactionRow] = field(default_factory=list)
    validation_errors: list[ImportIssue] = field(default_factory=list)


def parse_normalized_csv(csv_content: bytes) -> CsvParseResult:
    """Parse UTF-8 normalized bank-style CSV content without performing database work."""

    try:
        text_content = csv_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return CsvParseResult(
            validation_errors=[
                ImportIssue(code="invalid_encoding", message="CSV file must use UTF-8 encoding.")
            ]
        )

    reader = csv.DictReader(StringIO(text_content))
    fieldnames = set(reader.fieldnames or [])
    missing_columns = sorted(REQUIRED_COLUMNS - fieldnames)
    if missing_columns:
        return CsvParseResult(
            validation_errors=[
                ImportIssue(
                    row_number=1,
                    code="missing_required_columns",
                    message=f"Missing required CSV columns: {', '.join(missing_columns)}.",
                )
            ]
        )

    result = CsvParseResult()
    for row_number, row in enumerate(reader, start=2):
        result.rows_read += 1
        parsed_row, issues = _parse_row(row_number, row)
        if issues:
            result.validation_errors.extend(issues)
        elif parsed_row is not None:
            result.valid_rows.append(parsed_row)

    return result


def normalized_description(description: str) -> str:
    """Normalize only for duplicate comparisons; never replace the stored bank description."""

    return " ".join(description.split()).casefold()


def transaction_fingerprint(row: ParsedTransactionRow) -> tuple[date, Decimal, str, str, str]:
    """Create the approved fallback fingerprint excluding the account, supplied by import context."""

    return (
        row.transaction_date,
        row.amount,
        row.transaction_type,
        normalized_description(row.description),
        (row.reference or "").strip().casefold(),
    )


def _parse_row(row_number: int, row: dict[str | None, str | None]) -> tuple[ParsedTransactionRow | None, list[ImportIssue]]:
    if None in row:
        return None, [
            ImportIssue(
                row_number=row_number,
                code="malformed_row",
                message="Row contains more values than the CSV header defines.",
            )
        ]

    issues: list[ImportIssue] = []
    raw_date = _value(row, "transaction_date")
    raw_description = row.get("description") or ""
    raw_debit = _value(row, "debit")
    raw_credit = _value(row, "credit")
    raw_balance = _value(row, "balance")
    raw_reference = _value(row, "reference")
    raw_currency = _value(row, "currency")

    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError:
        parsed_date = None
        issues.append(ImportIssue(row_number=row_number, field="transaction_date", code="invalid_date", message="Transaction date must use YYYY-MM-DD."))

    if not raw_description.strip():
        issues.append(ImportIssue(row_number=row_number, field="description", code="empty_description", message="Description cannot be empty."))

    if raw_currency != "GBP":
        issues.append(ImportIssue(row_number=row_number, field="currency", code="invalid_currency", message="Currency must be GBP."))

    debit = _parse_money(raw_debit, "debit", row_number, issues)
    credit = _parse_money(raw_credit, "credit", row_number, issues)

    if debit is not None and credit is not None:
        issues.append(ImportIssue(row_number=row_number, code="both_debit_and_credit", message="Only one of debit or credit may be populated."))
    elif debit is None and credit is None and not any(issue.field in {"debit", "credit"} for issue in issues):
        issues.append(ImportIssue(row_number=row_number, code="missing_debit_and_credit", message="One of debit or credit must be populated."))

    balance = _parse_balance(raw_balance, row_number, issues)
    if issues or parsed_date is None:
        return None, issues

    amount = debit if debit is not None else credit
    transaction_type = "expense" if debit is not None else "income"
    return (
        ParsedTransactionRow(
            row_number=row_number,
            transaction_date=parsed_date,
            description=raw_description,
            amount=amount,
            transaction_type=transaction_type,
            balance=balance,
            reference=raw_reference or None,
        ),
        [],
    )


def _value(row: dict[str | None, str | None], field: str) -> str:
    return (row.get(field) or "").strip()


def _parse_money(value: str, field: str, row_number: int, issues: list[ImportIssue]) -> Decimal | None:
    if not value:
        return None
    if not _AMOUNT_PATTERN.fullmatch(value):
        issues.append(ImportIssue(row_number=row_number, field=field, code="invalid_amount", message=f"{field.title()} must be a positive decimal with up to two places."))
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation:
        issues.append(ImportIssue(row_number=row_number, field=field, code="invalid_amount", message=f"{field.title()} must be a valid decimal."))
        return None
    if amount <= 0:
        issues.append(ImportIssue(row_number=row_number, field=field, code="invalid_amount", message=f"{field.title()} must be greater than zero."))
        return None
    return amount


def _parse_balance(value: str, row_number: int, issues: list[ImportIssue]) -> Decimal | None:
    if not value:
        return None
    if not _BALANCE_PATTERN.fullmatch(value):
        issues.append(ImportIssue(row_number=row_number, field="balance", code="invalid_balance", message="Balance must be a decimal with up to two places."))
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        issues.append(ImportIssue(row_number=row_number, field="balance", code="invalid_balance", message="Balance must be a valid decimal."))
        return None
