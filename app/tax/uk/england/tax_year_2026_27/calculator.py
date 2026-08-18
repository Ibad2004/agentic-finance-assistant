"""Deterministic calculation engine for England Income Tax (tax year 2026/27).

Strictly deterministic Python logic using Decimal arithmetic.
Free of LLM logic and database dependencies.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

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

TWOPLACES = Decimal("0.01")
FOURPLACES = Decimal("0.0001")


def _quantize_currency(value: Decimal) -> Decimal:
    """Quantize to 2 decimal places using standard financial half-up rounding."""
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def calculate_personal_allowance(
    total_income: Decimal,
    custom_allowance: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    """Calculate standard Personal Allowance subject to the statutory £100,000 taper.

    Returns:
        (personal_allowance, reduction_amount)
    """
    if custom_allowance is not None:
        if custom_allowance < Decimal("0.00"):
            raise ValueError("Custom allowance cannot be negative.")
        return _quantize_currency(custom_allowance), Decimal("0.00")

    if total_income <= PERSONAL_ALLOWANCE_INCOME_LIMIT:
        return STANDARD_PERSONAL_ALLOWANCE, Decimal("0.00")

    if total_income >= PERSONAL_ALLOWANCE_ZERO_THRESHOLD:
        return Decimal("0.00"), STANDARD_PERSONAL_ALLOWANCE

    excess_income = total_income - PERSONAL_ALLOWANCE_INCOME_LIMIT
    reduction = _quantize_currency(excess_income * PERSONAL_ALLOWANCE_TAPER_RATE)
    allowance = max(Decimal("0.00"), STANDARD_PERSONAL_ALLOWANCE - reduction)
    return _quantize_currency(allowance), reduction


def calculate_england_income_tax_2026_27(
    total_income: Decimal,
    custom_allowance: Decimal | None = None,
) -> TaxCalculationResult:
    """Pure deterministic calculation of England Income Tax for tax year 2026/27."""
    if not isinstance(total_income, Decimal):
        raise TypeError(f"total_income must be a Decimal instance, got {type(total_income).__name__}.")

    if total_income < Decimal("0.00"):
        raise ValueError(f"total_income cannot be negative, got {total_income}.")

    income = _quantize_currency(total_income)

    personal_allowance, reduction = calculate_personal_allowance(income, custom_allowance)
    total_allowances = personal_allowance
    taxable_income = max(Decimal("0.00"), income - total_allowances)

    # Band 1: Basic Rate (20%) on first £37,700 of taxable income
    basic_taxable = min(taxable_income, BASIC_RATE_BAND_LIMIT)
    basic_tax = _quantize_currency(basic_taxable * BASIC_RATE)

    # Band 2: Higher Rate (40%) on taxable income between £37,700.01 and £125,140.00
    higher_taxable = max(
        Decimal("0.00"),
        min(taxable_income, HIGHER_RATE_BAND_LIMIT) - BASIC_RATE_BAND_LIMIT,
    )
    higher_tax = _quantize_currency(higher_taxable * HIGHER_RATE)

    # Band 3: Additional Rate (45%) on taxable income above £125,140.00
    additional_taxable = max(
        Decimal("0.00"),
        taxable_income - HIGHER_RATE_BAND_LIMIT,
    )
    additional_tax = _quantize_currency(additional_taxable * ADDITIONAL_RATE)

    total_tax_due = _quantize_currency(basic_tax + higher_tax + additional_tax)

    # Effective rate = total_tax_due / total_income
    effective_tax_rate = (
        (total_tax_due / income).quantize(FOURPLACES, rounding=ROUND_HALF_UP)
        if income > Decimal("0.00")
        else Decimal("0.0000")
    )

    # Marginal rate calculation (rate applied to the marginal £1 of income)
    if income == Decimal("0.00") or taxable_income == Decimal("0.00"):
        marginal_tax_rate = Decimal("0.00")
    elif income <= PERSONAL_ALLOWANCE_INCOME_LIMIT:
        marginal_tax_rate = BASIC_RATE if taxable_income <= BASIC_RATE_BAND_LIMIT else HIGHER_RATE
    elif income < PERSONAL_ALLOWANCE_ZERO_THRESHOLD:
        # In the taper zone (£100,000 - £125,140), losing £0.50 allowance per £1 creates a 60% effective marginal rate
        marginal_tax_rate = Decimal("0.60")
    elif taxable_income <= HIGHER_RATE_BAND_LIMIT:
        marginal_tax_rate = HIGHER_RATE
    else:
        marginal_tax_rate = ADDITIONAL_RATE

    bands = [
        TaxBandBreakdown(
            band_name="Basic Rate (20%)",
            rate=BASIC_RATE,
            taxable_amount=basic_taxable,
            tax_due=basic_tax,
        ),
        TaxBandBreakdown(
            band_name="Higher Rate (40%)",
            rate=HIGHER_RATE,
            taxable_amount=higher_taxable,
            tax_due=higher_tax,
        ),
        TaxBandBreakdown(
            band_name="Additional Rate (45%)",
            rate=ADDITIONAL_RATE,
            taxable_amount=additional_taxable,
            tax_due=additional_tax,
        ),
    ]

    calculation_details = {
        "jurisdiction": JURISDICTION,
        "tax_year": TAX_YEAR,
        "rules_version": RULES_VERSION,
        "official_source_url": OFFICIAL_SOURCE_URL,
        "total_income": str(income),
        "personal_allowance": str(personal_allowance),
        "personal_allowance_reduction": str(reduction),
        "taper_applied": reduction > Decimal("0.00"),
        "total_allowances": str(total_allowances),
        "taxable_income": str(taxable_income),
        "bands_breakdown": [
            {
                "band_name": b.band_name,
                "rate": str(b.rate),
                "taxable_amount": str(b.taxable_amount),
                "tax_due": str(b.tax_due),
            }
            for b in bands
        ],
        "income_tax_due": str(total_tax_due),
        "effective_tax_rate": str(effective_tax_rate),
        "marginal_tax_rate": str(marginal_tax_rate),
        "is_estimate": True,
    }

    return TaxCalculationResult(
        tax_year=TAX_YEAR,
        rules_version=RULES_VERSION,
        jurisdiction=JURISDICTION,
        official_source_url=OFFICIAL_SOURCE_URL,
        total_income=income,
        personal_allowance=personal_allowance,
        total_allowances=total_allowances,
        taxable_income=taxable_income,
        income_tax_due=total_tax_due,
        effective_tax_rate=effective_tax_rate,
        marginal_tax_rate=marginal_tax_rate,
        bands=bands,
        calculation_details=calculation_details,
        assumptions=ASSUMPTIONS,
        limitations=LIMITATIONS,
        is_estimate=True,
    )
