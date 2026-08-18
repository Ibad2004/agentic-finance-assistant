"""Pydantic schemas for financial report generation and retrieval."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportGenerateRequest(BaseModel):
    """Request to generate a financial report."""

    report_type: str = Field(
        default="monthly_summary",
        description="Type of report: monthly_summary, expense_summary, tax_summary",
    )
    period_start: date
    period_end: date

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, value: str) -> str:
        allowed = {"monthly_summary", "expense_summary", "tax_summary"}
        if value not in allowed:
            raise ValueError(f"report_type must be one of: {', '.join(sorted(allowed))}")
        return value


class ReportResponse(BaseModel):
    """Response for a financial report metadata record."""

    id: UUID
    report_type: str
    period_start: date
    period_end: date
    file_format: str
    storage_path: str
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportDetailResponse(ReportResponse):
    """Detailed report response including summary data."""

    total_income: float = 0.0
    total_expenses: float = 0.0
    net_amount: float = 0.0
    transaction_count: int = 0
    category_breakdown: dict[str, float] = Field(default_factory=dict)
