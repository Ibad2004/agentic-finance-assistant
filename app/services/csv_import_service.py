"""CSV import orchestration using validation and controlled repository access."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import Transaction
from app.db.repositories.transaction_repository import TransactionRepository
from app.schemas.csv_import import CsvImportResult, ImportIssue
from app.services.csv_parser import (
    ParsedTransactionRow,
    normalized_description,
    parse_normalized_csv,
    transaction_fingerprint,
)


class CsvImportService:
    """Imports validated normalized CSV rows without delegating any work to an LLM."""

    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    def import_csv(self, *, user_id: UUID, account_id: UUID, csv_content: bytes) -> CsvImportResult:
        """Validate, de-duplicate, and persist a CSV import for one authenticated account owner."""

        account = self._repository.get_account_for_user(account_id, user_id)
        if account is None:
            return CsvImportResult(
                validation_errors=[
                    ImportIssue(code="account_not_found", message="The selected financial account is unavailable.")
                ]
            )

        parsed = parse_normalized_csv(csv_content)
        result = CsvImportResult(
            rows_read=parsed.rows_read,
            rows_rejected=len(parsed.validation_errors),
            validation_errors=list(parsed.validation_errors),
        )
        if not parsed.valid_rows:
            return result

        rows_to_import = self._filter_duplicates(account_id, parsed.valid_rows, result)
        if not rows_to_import:
            return result

        transactions = [
            Transaction(
                user_id=user_id,
                account_id=account_id,
                category_id=None,
                transaction_date=row.transaction_date,
                description=row.description,
                amount=row.amount,
                transaction_type=row.transaction_type,
                source="csv",
                source_reference=row.reference,
                is_reviewed=False,
            )
            for row in rows_to_import
        ]

        try:
            self._repository.add_transactions(transactions)
            latest_balance_row = max(
                (row for row in rows_to_import if row.balance is not None),
                key=lambda row: (row.transaction_date, row.row_number),
                default=None,
            )
            if latest_balance_row is not None and latest_balance_row.balance is not None:
                self._repository.update_account_balance(account, latest_balance_row.balance, datetime.now(UTC))
            self._repository.commit()
        except SQLAlchemyError:
            self._repository.rollback()
            return CsvImportResult(
                rows_read=parsed.rows_read,
                rows_rejected=len(parsed.validation_errors),
                duplicate_rows=result.duplicate_rows,
                possible_duplicate_rows=result.possible_duplicate_rows,
                validation_errors=[
                    *parsed.validation_errors,
                    ImportIssue(code="import_failed", message="The CSV import could not be completed safely."),
                ],
            )

        result.rows_imported = len(transactions)
        result.imported_transaction_ids = [transaction.id for transaction in transactions]
        return result

    def _filter_duplicates(
        self,
        account_id: UUID,
        valid_rows: Iterable[ParsedTransactionRow],
        result: CsvImportResult,
    ) -> list[ParsedTransactionRow]:
        rows = list(valid_rows)
        existing_by_reference = {
            transaction.source_reference: transaction
            for transaction in self._repository.find_transactions_by_source_references(
                account_id, {row.reference for row in rows if row.reference}
            )
            if transaction.source_reference
        }
        seen_references: set[str] = set()
        seen_fingerprints: set[tuple] = set()
        accepted_rows: list[ParsedTransactionRow] = []

        for row in rows:
            fingerprint = transaction_fingerprint(row)
            if row.reference and (row.reference in existing_by_reference or row.reference in seen_references):
                result.duplicate_rows += 1
                result.validation_errors.append(
                    ImportIssue(row_number=row.row_number, code="duplicate_transaction", message="Duplicate transaction reference detected.")
                )
                continue

            if fingerprint in seen_fingerprints or self._has_database_fingerprint_match(account_id, row):
                result.possible_duplicate_rows += 1
                result.validation_errors.append(
                    ImportIssue(row_number=row.row_number, code="possible_duplicate", message="Possible duplicate transaction requires review.")
                )
                continue

            if row.reference:
                seen_references.add(row.reference)
            seen_fingerprints.add(fingerprint)
            accepted_rows.append(row)

        return accepted_rows

    def _has_database_fingerprint_match(self, account_id: UUID, row: ParsedTransactionRow) -> bool:
        target = transaction_fingerprint(row)
        candidates = self._repository.find_fingerprint_candidates(
            account_id, row.transaction_date, row.amount, row.transaction_type
        )
        return any(
            (
                candidate.transaction_date,
                candidate.amount,
                candidate.transaction_type,
                normalized_description(candidate.description),
                (candidate.source_reference or "").strip().casefold(),
            )
            == target
            for candidate in candidates
        )
