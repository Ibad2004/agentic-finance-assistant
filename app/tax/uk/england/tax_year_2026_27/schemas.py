"""Data models and schemas for England Income Tax (2026/27) calculations."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.tax.uk.england.tax_year_2026_27.rules import (
    ASSUMPTIONS,
    JURISDICTION,
    LIMITATIONS,
    OFFICIAL_SOURCE_URL,
    RULES_VERSION,
    TAX_YEAR,
)


class TaxBandBreakdown(BaseModel):
    """Breakdown of income tax calculated in a specific tax band."""

    band_name: str
    rate: Decimal
    taxable_amount: Decimal
    tax_due: Decimal

    model_config = ConfigDict(from_attributes=True)


class TaxCalculationResult(BaseModel):
    """Complete structured result of an England Income Tax 2026/27 estimation."""

    tax_year: str = TAX_YEAR
    rules_version: str = RULES_VERSION
    jurisdiction: str = JURISDICTION
    official_source_url: str = OFFICIAL_SOURCE_URL
    total_income: Decimal
    personal_allowance: Decimal
    total_allowances: Decimal
    taxable_income: Decimal
    income_tax_due: Decimal
    effective_tax_rate: Decimal = Field(description="Total tax due divided by total income (0.00 to 1.00)")
    marginal_tax_rate: Decimal = Field(description="Tax rate applied to the last pound of income")
    bands: list[TaxBandBreakdown]
    calculation_details: dict[str, Any]
    assumptions: str = ASSUMPTIONS
    limitations: str = LIMITATIONS
    is_estimate: bool = True

    model_config = ConfigDict(from_attributes=True)
