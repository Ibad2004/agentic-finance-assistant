from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.db.models import FinancialAccount, Transaction
from app.services.csv_import_service import CsvImportService


HEADER = "transaction_date,description,debit,credit,balance,reference,currency\n"


class FakeTransactionRepository:
    def __init__(self, account: FinancialAccount | None, existing: list[Transaction] | None = None) -> None:
        self.account = account
        self.existing = existing or []
        self.added: list[Transaction] = []
        self.committed = False
        self.balance_update: tuple[Decimal, datetime] | None = None

    def get_account_for_user(self, account_id: UUID, user_id: UUID) -> FinancialAccount | None:
        if self.account and self.account.id == account_id and self.account.user_id == user_id:
            return self.account
        return None

    def find_transactions_by_source_references(self, account_id: UUID, source_references: set[str]) -> list[Transaction]:
        return [
            transaction
            for transaction in self.existing
            if transaction.account_id == account_id and transaction.source_reference in source_references
        ]

    def find_fingerprint_candidates(
        self, account_id: UUID, transaction_date, amount: Decimal, transaction_type: str
    ) -> list[Transaction]:
        return [
            transaction
            for transaction in self.existing
            if transaction.account_id == account_id
            and transaction.transaction_date == transaction_date
            and transaction.amount == amount
            and transaction.transaction_type == transaction_type
        ]

    def add_transactions(self, transactions: list[Transaction]) -> None:
        for transaction in transactions:
            transaction.id = uuid4()
        self.added.extend(transactions)

    def update_account_balance(self, account: FinancialAccount, balance: Decimal, updated_at: datetime) -> None:
        account.current_balance = balance
        account.balance_updated_at = updated_at
        self.balance_update = (balance, updated_at)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        raise AssertionError("Rollback should not be needed in this test.")


def make_account(user_id: UUID | None = None) -> FinancialAccount:
    return FinancialAccount(id=uuid4(), user_id=user_id or uuid4(), account_name="Main Account", account_type="current")


def import_content(rows: list[str]) -> bytes:
    return (HEADER + "\n".join(rows) + "\n").encode()


def test_duplicate_within_same_csv_is_rejected() -> None:
    account = make_account()
    repository = FakeTransactionRepository(account)
    result = CsvImportService(repository).import_csv(
        user_id=account.user_id,
        account_id=account.id,
        csv_content=import_content(
            [
                "2026-04-07,TESCO,10.00,,,SAME-REFERENCE,GBP",
                "2026-04-08,TESCO,10.00,,,SAME-REFERENCE,GBP",
            ]
        ),
    )

    assert result.rows_imported == 1
    assert result.duplicate_rows == 1
    assert len(repository.added) == 1


def test_duplicate_already_in_database_is_rejected() -> None:
    account = make_account()
    existing = Transaction(
        id=uuid4(), user_id=account.user_id, account_id=account.id,
        transaction_date=date(2026, 4, 7), description="TESCO", amount=Decimal("10.00"),
        transaction_type="expense", source="csv", source_reference="TESCO-REF", is_reviewed=False,
    )
    repository = FakeTransactionRepository(account, [existing])

    result = CsvImportService(repository).import_csv(
        user_id=account.user_id,
        account_id=account.id,
        csv_content=import_content(["2026-04-07,TESCO,10.00,,,TESCO-REF,GBP"]),
    )

    assert result.rows_imported == 0
    assert result.duplicate_rows == 1
    assert not repository.added


def test_fingerprint_match_without_reference_is_reported_as_possible_duplicate() -> None:
    account = make_account()
    existing = Transaction(
        id=uuid4(), user_id=account.user_id, account_id=account.id,
        transaction_date=date(2026, 4, 7), description="Tesco   Stores", amount=Decimal("10.00"),
        transaction_type="expense", source="csv", source_reference=None, is_reviewed=False,
    )
    repository = FakeTransactionRepository(account, [existing])

    result = CsvImportService(repository).import_csv(
        user_id=account.user_id,
        account_id=account.id,
        csv_content=import_content(["2026-04-07,TESCO STORES,10.00,,,,GBP"]),
    )

    assert result.rows_imported == 0
    assert result.possible_duplicate_rows == 1


def test_account_must_belong_to_authenticated_user() -> None:
    account = make_account()
    repository = FakeTransactionRepository(account)

    result = CsvImportService(repository).import_csv(
        user_id=uuid4(),
        account_id=account.id,
        csv_content=import_content(["2026-04-07,TESCO,10.00,,,REF,GBP"]),
    )

    assert result.rows_imported == 0
    assert result.validation_errors[0].code == "account_not_found"
    assert not repository.added


def test_latest_valid_balance_updates_selected_account() -> None:
    account = make_account()
    repository = FakeTransactionRepository(account)
    result = CsvImportService(repository).import_csv(
        user_id=account.user_id,
        account_id=account.id,
        csv_content=import_content(
            [
                "2026-04-06,ACME PAYROLL,,100.00,100.00,PAYROLL,GBP",
                "2026-04-08,TESCO,25.50,,74.50,TESCO-REF,GBP",
            ]
        ),
    )

    assert result.rows_imported == 2
    assert account.current_balance == Decimal("74.50")
    assert repository.balance_update is not None
    assert repository.committed
    imported_expense = repository.added[1]
    assert imported_expense.category_id is None
    assert imported_expense.source == "csv"
    assert imported_expense.is_reviewed is False
