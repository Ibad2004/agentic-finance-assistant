"""England Income Tax (tax year 2026/27) package."""

from app.tax.uk.england.tax_year_2026_27.calculator import (
    calculate_england_income_tax_2026_27,
    calculate_personal_allowance,
)
from app.tax.uk.england.tax_year_2026_27.rules import (
    ADDITIONAL_RATE,
    ASSUMPTIONS,
    BASIC_RATE,
    BASIC_RATE_BAND_LIMIT,
    HIGHER_RATE,
    HIGHER_RATE_BAND_LIMIT,
    JURISDICTION,
    LIMITATIONS,
    OFFICIAL_SOURCE_URL,
    PERSONAL_ALLOWANCE_INCOME_LIMIT,
    PERSONAL_ALLOWANCE_TAPER_RATE,
    PERSONAL_ALLOWANCE_ZERO_THRESHOLD,
    RULES_VERSION,
    STANDARD_PERSONAL_ALLOWANCE,
    TAX_YEAR,
)
from app.tax.uk.england.tax_year_2026_27.schemas import (
    TaxBandBreakdown,
    TaxCalculationResult,
)

__all__ = [
    "ADDITIONAL_RATE",
    "ASSUMPTIONS",
    "BASIC_RATE",
    "BASIC_RATE_BAND_LIMIT",
    "HIGHER_RATE",
    "HIGHER_RATE_BAND_LIMIT",
    "JURISDICTION",
    "LIMITATIONS",
    "OFFICIAL_SOURCE_URL",
    "PERSONAL_ALLOWANCE_INCOME_LIMIT",
    "PERSONAL_ALLOWANCE_TAPER_RATE",
    "PERSONAL_ALLOWANCE_ZERO_THRESHOLD",
    "RULES_VERSION",
    "STANDARD_PERSONAL_ALLOWANCE",
    "TAX_YEAR",
    "TaxBandBreakdown",
    "TaxCalculationResult",
    "calculate_england_income_tax_2026_27",
    "calculate_personal_allowance",
]
