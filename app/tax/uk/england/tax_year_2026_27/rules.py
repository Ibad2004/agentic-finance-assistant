"""Official England Income Tax rules, rates, and thresholds for tax year 2026/27.

Source of Truth:
Official GOV.UK Income Tax rates and allowances (verified for tax year 2026/27).
https://www.gov.uk/income-tax-rates
"""

from __future__ import annotations

from decimal import Decimal

TAX_YEAR: str = "2026/27"
RULES_VERSION: str = "2026_27_england_v1"
JURISDICTION: str = "United Kingdom: England"
OFFICIAL_SOURCE_URL: str = "https://www.gov.uk/income-tax-rates"

# Statutory Allowances & Thresholds (England 2026/27)
STANDARD_PERSONAL_ALLOWANCE: Decimal = Decimal("12570.00")
PERSONAL_ALLOWANCE_INCOME_LIMIT: Decimal = Decimal("100000.00")
PERSONAL_ALLOWANCE_TAPER_RATE: Decimal = Decimal("0.50")  # £1 reduction for every £2 above £100,000
PERSONAL_ALLOWANCE_ZERO_THRESHOLD: Decimal = Decimal("125140.00")  # £100,000 + 2 * £12,570

# Taxable Income Bands (England 2026/27)
# Band 1: Basic Rate (20%) on first £37,700 of taxable income
BASIC_RATE_BAND_LIMIT: Decimal = Decimal("37700.00")

# Band 2: Higher Rate (40%) on taxable income between £37,700.01 and £125,140.00 (width: £87,440.00)
HIGHER_RATE_BAND_LIMIT: Decimal = Decimal("125140.00")

# Band Rates
BASIC_RATE: Decimal = Decimal("0.20")
HIGHER_RATE: Decimal = Decimal("0.40")
ADDITIONAL_RATE: Decimal = Decimal("0.45")

ASSUMPTIONS: str = (
    "Taxpayer is a UK resident with tax residence in England for the 2026/27 tax year "
    "(6 April 2026 to 5 April 2027). All income is treated as non-savings, non-dividend "
    "income (such as employment salary, self-employment profits, or pension income). "
    "Standard Personal Allowance of £12,570.00 is applied, subject to statutory taper "
    "reduction above £100,000.00 adjusted net income. Does not include marriage allowance, "
    "blind person's allowance, or bespoke pension tax relief adjustments."
)

LIMITATIONS: str = (
    "This calculation is an automated deterministic estimate for England Income Tax (2026/27) "
    "only and does NOT constitute an official HMRC tax determination, assessment, or binding advice. "
    "Excludes Scottish and Welsh devolved income tax rates, National Insurance Contributions (NICs), "
    "VAT, Capital Gains Tax, Dividend Allowance, Personal Savings Allowance, High Income Child Benefit "
    "Charge, Student Loan repayments, and HMRC tax filing/submission capabilities."
)
