"""Pydantic schemas for tax estimation and calculations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.tax.uk.england.tax_year_2026_27.schemas import (
    TaxCalculationResult as EngineTaxCalculationResult,
)


class TaxEstimateRequest(BaseModel):
    """Request for estimating income tax."""

    total_income: Decimal = Field(
        gt=0,
        description="Total income for the tax year (must be positive)",
    )

    custom_allowance: Decimal | None = Field(
        default=None,
        ge=0,
        description="Custom allowance to override standard Personal Allowance",
    )

    @field_validator("total_income", "custom_allowance")
    @classmethod
    def non_negative(
        cls,
        value: Decimal | None,
    ) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("Value must be non-negative")
        return value


class TaxCalculationResponse(BaseModel):
    """Response for a tax calculation (persisted or estimated)."""

    id: UUID | None = None
    user_id: UUID | None = None

    tax_year: str
    rules_version: str
    calculated_at: datetime | None = None

    # API response values are floats so they serialize as JSON numbers.
    # The actual tax engine continues to use Decimal for financial accuracy.
    total_income: float
    total_allowances: float
    taxable_income: float
    income_tax_due: float

    effective_tax_rate: float = Field(
        description="Total tax due divided by total income (0.00 to 1.00)",
    )

    marginal_tax_rate: float = Field(
        description="Tax rate applied to the last pound of income",
    )

    band_breakdown: list[dict[str, Any]] = Field(
        description="Breakdown of tax by band",
    )

    assumptions: str
    limitations: str

    calculation_details: dict[str, Any] | None = None

    is_estimate: bool = True

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_engine_result(
        cls,
        result: EngineTaxCalculationResult,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        calculated_at: datetime | None = None,
    ) -> "TaxCalculationResponse":
        """Create an API response from the tax engine's result."""

        return cls(
            id=id,
            user_id=user_id,
            tax_year=result.tax_year,
            rules_version=result.rules_version,
            calculated_at=calculated_at,

            # Convert Decimal -> float for JSON API response.
            total_income=float(result.total_income),
            total_allowances=float(result.total_allowances),
            taxable_income=float(result.taxable_income),
            income_tax_due=float(result.income_tax_due),
            effective_tax_rate=float(result.effective_tax_rate),
            marginal_tax_rate=float(result.marginal_tax_rate),

            band_breakdown=[
                {
                    "band_name": band.band_name,
                    "rate": float(band.rate),
                    "taxable_amount": float(band.taxable_amount),
                    "tax_due": float(band.tax_due),
                }
                for band in result.bands
            ],

            assumptions=result.assumptions,
            limitations=result.limitations,
            calculation_details=result.calculation_details,
            is_estimate=result.is_estimate,
        )