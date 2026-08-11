"""Controlled entry point for importing normalized CSV financial transactions."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repositories.transaction_repository import TransactionRepository
from app.schemas.csv_import import CsvImportResult
from app.services.csv_import_service import CsvImportService


def import_csv_transactions(
    *, session: Session, authenticated_user_id: UUID, selected_account_id: UUID, csv_content: bytes
) -> CsvImportResult:
    """Import a CSV only for the authenticated owner of the selected account."""

    service = CsvImportService(TransactionRepository(session))
    return service.import_csv(
        user_id=authenticated_user_id,
        account_id=selected_account_id,
        csv_content=csv_content,
    )
