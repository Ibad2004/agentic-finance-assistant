"""Deterministic unit tests for England Income Tax (tax year 2026/27).

Verified against official GOV.UK Income Tax rates and allowances:
https://www.gov.uk/income-tax-rates
"""

from decimal import Decimal
import pytest

from app.tax.uk.england.tax_year_2026_27.calculator import (
    calculate_england_income_tax_2026_27,
    calculate_personal_allowance,
)
from app.tax.uk.england.tax_year_2026_27.rules import (
    OFFICIAL_SOURCE_URL,
    RULES_VERSION,
    STANDARD_PERSONAL_ALLOWANCE,
    TAX_YEAR,
)


def test_zero_income_produces_zero_tax() -> None:
    result = calculate_england_income_tax_2026_27(Decimal("0.00"))
    assert result.total_income == Decimal("0.00")
    assert result.personal_allowance == STANDARD_PERSONAL_ALLOWANCE
    assert result.taxable_income == Decimal("0.00")
    assert result.income_tax_due == Decimal("0.00")
    assert result.effective_tax_rate == Decimal("0.0000")
    assert result.marginal_tax_rate == Decimal("0.00")


def test_income_at_exact_personal_allowance_limit() -> None:
    result = calculate_england_income_tax_2026_27(Decimal("12570.00"))
    assert result.total_income == Decimal("12570.00")
    assert result.personal_allowance == Decimal("12570.00")
    assert result.taxable_income == Decimal("0.00")
    assert result.income_tax_due == Decimal("0.00")
    assert result.effective_tax_rate == Decimal("0.0000")


def test_income_one_pound_above_personal_allowance() -> None:
    result = calculate_england_income_tax_2026_27(Decimal("12571.00"))
    assert result.total_income == Decimal("12571.00")
    assert result.personal_allowance == Decimal("12570.00")
    assert result.taxable_income == Decimal("1.00")
    # £1.00 taxable @ 20% = £0.20
    assert result.income_tax_due == Decimal("0.20")
    assert result.marginal_tax_rate == Decimal("0.20")


def test_basic_rate_income_calculation() -> None:
    # £30,000 income: £12,570 allowance, £17,430 taxable @ 20% = £3,486.00
    result = calculate_england_income_tax_2026_27(Decimal("30000.00"))
    assert result.personal_allowance == Decimal("12570.00")
    assert result.taxable_income == Decimal("17430.00")
    assert result.income_tax_due == Decimal("3486.00")
    assert result.bands[0].taxable_amount == Decimal("17430.00")
    assert result.bands[0].tax_due == Decimal("3486.00")
    assert result.bands[1].tax_due == Decimal("0.00")
    assert result.bands[2].tax_due == Decimal("0.00")
    assert result.effective_tax_rate == Decimal("0.1162")  # 3486 / 30000
    assert result.marginal_tax_rate == Decimal("0.20")


def test_income_at_basic_rate_ceiling() -> None:
    # £50,270 income (£12,570 + £37,700 basic band) -> £37,700 taxable @ 20% = £7,540.00
    result = calculate_england_income_tax_2026_27(Decimal("50270.00"))
    assert result.taxable_income == Decimal("37700.00")
    assert result.income_tax_due == Decimal("7540.00")
    assert result.bands[0].tax_due == Decimal("7540.00")
    assert result.bands[1].tax_due == Decimal("0.00")
    assert result.marginal_tax_rate == Decimal("0.20")


def test_higher_rate_income_calculation() -> None:
    # £60,000 income: £12,570 allowance, £47,430 taxable.
    # Basic (£37,700 @ 20% = £7,540) + Higher (£9,730 @ 40% = £3,892) = £11,432.00
    result = calculate_england_income_tax_2026_27(Decimal("60000.00"))
    assert result.taxable_income == Decimal("47430.00")
    assert result.bands[0].tax_due == Decimal("7540.00")
    assert result.bands[1].tax_due == Decimal("3892.00")
    assert result.income_tax_due == Decimal("11432.00")
    assert result.marginal_tax_rate == Decimal("0.40")


def test_income_at_exact_taper_threshold() -> None:
    # £100,000 income: £12,570 allowance, £87,430 taxable.
    # Basic (£37,700 @ 20% = £7,540) + Higher (£49,730 @ 40% = £19,892) = £27,432.00
    result = calculate_england_income_tax_2026_27(Decimal("100000.00"))
    assert result.personal_allowance == Decimal("12570.00")
    assert result.taxable_income == Decimal("87430.00")
    assert result.income_tax_due == Decimal("27432.00")
    assert result.marginal_tax_rate == Decimal("0.40")


def test_personal_allowance_taper_reduction() -> None:
    # £110,000 income: £10,000 excess over £100,000. Taper reduction = £5,000.
    # Allowance = £12,570 - £5,000 = £7,570.
    # Taxable income = £110,000 - £7,570 = £102,430.
    # Basic: £37,700 @ 20% = £7,540.
    # Higher: £64,730 @ 40% = £25,892.
    # Total tax = £7,540 + £25,892 = £33,432.00.
    result = calculate_england_income_tax_2026_27(Decimal("110000.00"))
    assert result.personal_allowance == Decimal("7570.00")
    assert result.taxable_income == Decimal("102430.00")
    assert result.income_tax_due == Decimal("33432.00")
    # Effective marginal rate in the £100k-£125k taper trap is 60%
    assert result.marginal_tax_rate == Decimal("0.60")


def test_income_at_exact_zero_allowance_boundary() -> None:
    # £125,140 income: Personal Allowance reduced to £0.00.
    # Taxable income = £125,140.
    # Basic: £37,700 @ 20% = £7,540.
    # Higher: £87,440 @ 40% = £34,976.
    # Total tax = £42,516.00.
    result = calculate_england_income_tax_2026_27(Decimal("125140.00"))
    assert result.personal_allowance == Decimal("0.00")
    assert result.taxable_income == Decimal("125140.00")
    assert result.income_tax_due == Decimal("42516.00")
    assert result.bands[2].tax_due == Decimal("0.00")


def test_additional_rate_income_calculation() -> None:
    # £150,000 income: Personal Allowance = £0. Taxable = £150,000.
    # Basic: £37,700 @ 20% = £7,540.
    # Higher: £87,440 @ 40% = £34,976.
    # Additional: (£150,000 - £125,140) = £24,860 @ 45% = £11,187.00.
    # Total tax = £7,540 + £34,976 + £11,187 = £53,703.00.
    result = calculate_england_income_tax_2026_27(Decimal("150000.00"))
    assert result.personal_allowance == Decimal("0.00")
    assert result.taxable_income == Decimal("150000.00")
    assert result.bands[0].tax_due == Decimal("7540.00")
    assert result.bands[1].tax_due == Decimal("34976.00")
    assert result.bands[2].taxable_amount == Decimal("24860.00")
    assert result.bands[2].tax_due == Decimal("11187.00")
    assert result.income_tax_due == Decimal("53703.00")
    assert result.marginal_tax_rate == Decimal("0.45")


def test_custom_allowance_override() -> None:
    # £30,000 income with £15,000 custom allowance -> £15,000 taxable @ 20% = £3,000.00
    result = calculate_england_income_tax_2026_27(
        Decimal("30000.00"),
        custom_allowance=Decimal("15000.00"),
    )
    assert result.personal_allowance == Decimal("15000.00")
    assert result.taxable_income == Decimal("15000.00")
    assert result.income_tax_due == Decimal("3000.00")


def test_negative_income_raises_value_error() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_england_income_tax_2026_27(Decimal("-100.00"))


def test_non_decimal_type_raises_type_error() -> None:
    with pytest.raises(TypeError, match="must be a Decimal"):
        calculate_england_income_tax_2026_27(50000.0)  # type: ignore[arg-type]


def test_metadata_and_assumptions_integrity() -> None:
    result = calculate_england_income_tax_2026_27(Decimal("45000.00"))
    assert result.tax_year == TAX_YEAR == "2026/27"
    assert result.rules_version == RULES_VERSION == "2026_27_england_v1"
    assert result.official_source_url == OFFICIAL_SOURCE_URL
    assert result.is_estimate is True
    assert "England" in result.assumptions
    assert "NOT constitute an official HMRC tax determination" in result.limitations
    assert isinstance(result.calculation_details, dict)
    assert result.calculation_details["is_estimate"] is True
