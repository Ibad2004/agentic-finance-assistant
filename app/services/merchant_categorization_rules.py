"""Small deterministic merchant rules used before any LLM request."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MerchantRule:
    pattern: re.Pattern[str]
    transaction_type: str
    category_name: str
    rule_id: str


@dataclass(frozen=True)
class DeterministicMatch:
    category_name: str
    confidence: float
    reason: str
    rule_id: str


MERCHANT_RULES = (
    MerchantRule(re.compile(r"\bTESCO\b", re.IGNORECASE), "expense", "Food", "tesco-food"),
    MerchantRule(re.compile(r"\bSAINSBURY'S\b", re.IGNORECASE), "expense", "Food", "sainsburys-food"),
    MerchantRule(re.compile(r"\bASDA\b", re.IGNORECASE), "expense", "Food", "asda-food"),
    MerchantRule(re.compile(r"\bMORRISONS\b", re.IGNORECASE), "expense", "Food", "morrisons-food"),
    MerchantRule(re.compile(r"\bTFL\b", re.IGNORECASE), "expense", "Transport", "tfl-transport"),
    MerchantRule(re.compile(r"\bUBER\b", re.IGNORECASE), "expense", "Transport", "uber-transport"),
    MerchantRule(re.compile(r"\bOCTOPUS ENERGY\b", re.IGNORECASE), "expense", "Utilities", "octopus-energy-utilities"),
    MerchantRule(re.compile(r"\bNETFLIX\b", re.IGNORECASE), "expense", "Subscriptions", "netflix-subscriptions"),
    MerchantRule(re.compile(r"\bPAYROLL\b", re.IGNORECASE), "income", "Salary", "payroll-salary"),
)


def normalize_for_matching(description: str) -> str:
    """Normalize a description for matching only; stored descriptions remain unchanged."""

    return " ".join(description.strip().split())


def match_merchant_rule(description: str, transaction_type: str) -> DeterministicMatch | None:
    """Return a match only when exactly one rule clearly applies to the transaction type."""

    normalized_description = normalize_for_matching(description)
    matches = [
        rule
        for rule in MERCHANT_RULES
        if rule.transaction_type == transaction_type and rule.pattern.search(normalized_description)
    ]
    if len(matches) != 1:
        return None
    rule = matches[0]
    return DeterministicMatch(
        category_name=rule.category_name,
        confidence=1.0,
        reason=f"Matched deterministic merchant rule: {rule.rule_id}.",
        rule_id=rule.rule_id,
    )
