"""Structured results returned by the CSV financial transaction import."""

from uuid import UUID

from pydantic import BaseModel, Field


class ImportIssue(BaseModel):
    """A row-level validation, duplicate, or safe persistence issue."""

    row_number: int | None = None
    field: str | None = None
    code: str
    message: str


class CsvImportResult(BaseModel):
    """Summary of a completed CSV import attempt."""

    rows_read: int = 0
    rows_imported: int = 0
    rows_rejected: int = 0
    duplicate_rows: int = 0
    possible_duplicate_rows: int = 0
    validation_errors: list[ImportIssue] = Field(default_factory=list)
    imported_transaction_ids: list[UUID] = Field(default_factory=list)
