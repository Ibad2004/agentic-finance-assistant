"""Tax Agent for coordinating England Income Tax estimation with AI explanation."""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.tools.tax_calculation_tool import calculate_and_record_tax_estimate

logger = logging.getLogger(__name__)

TAX_EXPLANATION_SYSTEM_PROMPT = """You are Finora's Tax Explanation AI. You explain England Income Tax (2026/27) calculations in clear, simple language.

RULES:
- ALL tax figures in your response MUST come from the verified calculation data provided.
- NEVER calculate, estimate, or invent any tax amounts.
- The total_income, personal_allowance, taxable_income, income_tax_due, and band breakdown are authoritative.
- Always remind the user this is an estimate, NOT an official HMRC determination.
- Explain tax bands in plain language.
- All amounts are in GBP (£).
- You are not a replacement for a qualified tax advisor.
"""


class TaxAgent:
    """Coordinates tax calculation workflow using deterministic engine, with AI explanation."""

    def __init__(self, session: Session, llm=None) -> None:
        self._session = session
        self._llm = llm

    def calculate_and_save(
        self,
        user_id: UUID,
        total_income: float | int | Decimal,
        custom_allowance: float | int | Decimal | None = None,
    ):
        """Calculate England Income Tax and persist the result for the user.

        This method is 100% deterministic. No LLM involvement.

        Args:
            user_id: The authenticated user's ID.
            total_income: Total income for the tax year.
            custom_allowance: Optional custom allowance.

        Returns:
            The persisted TaxCalculation model.
        """
        total_income_dec = Decimal(str(total_income))
        custom_allowance_dec = (
            Decimal(str(custom_allowance)) if custom_allowance is not None else None
        )

        return calculate_and_record_tax_estimate(
            session=self._session,
            authenticated_user_id=user_id,
            total_income=total_income_dec,
            custom_allowance=custom_allowance_dec,
        )

    def explain_tax(
        self,
        user_id: UUID,
        calculation_id: UUID,
    ) -> dict:
        """Explain an existing tax calculation using AI.

        Flow:
        1. Retrieve the persisted tax calculation (deterministic)
        2. Build verified financial context from the stored result
        3. AI explains the calculation using ONLY verified data

        The AI does NOT re-calculate. It only explains the existing result.
        """
        from app.db.repositories.tax_calculation_repository import TaxCalculationRepository

        repository = TaxCalculationRepository(self._session)
        calculation = repository.get_by_id(calculation_id, user_id)
        if calculation is None:
            return {"error": "Tax calculation not found or access denied."}

        verified_context = self._build_tax_context(calculation)

        if self._llm is None:
            return {
                "tax_data": verified_context,
                "ai_explanation": "AI explanation is not available. Please review the verified tax data.",
            }

        ai_explanation = self._get_ai_explanation(verified_context)

        return {
            "tax_data": {
                "tax_year": calculation.tax_year,
                "total_income": float(calculation.total_income),
                "total_allowances": float(calculation.total_allowances),
                "taxable_income": float(calculation.taxable_income),
                "income_tax_due": float(calculation.income_tax_due),
                "rules_version": calculation.rules_version,
                "assumptions": calculation.assumptions,
                "limitations": calculation.limitations,
            },
            "ai_explanation": ai_explanation,
        }

    def answer_tax_question(
        self,
        user_id: UUID,
        question: str,
    ) -> str:
        """Answer a natural language question about the user's tax situation.

        Flow:
        1. Retrieve the user's latest tax calculation (deterministic)
        2. Build verified financial context
        3. AI answers using ONLY verified data
        """
        from app.db.repositories.tax_calculation_repository import TaxCalculationRepository

        repository = TaxCalculationRepository(self._session)
        calculations = repository.list_for_user(user_id)

        if not calculations:
            return "You don't have any tax calculations yet. Use the tax estimate endpoint to calculate your income tax first."

        latest = calculations[0]
        verified_context = self._build_tax_context(latest)

        if self._llm is None:
            return f"AI is not available. Here is your verified tax data:\n{verified_context}"

        system_prompt = (
            f"{TAX_EXPLANATION_SYSTEM_PROMPT}\n\n"
            f"VERIFIED TAX CALCULATION DATA:\n{verified_context}\n\n"
            f"Answer the user's question using ONLY the verified data above. "
            f"If the data does not contain enough information, say so."
        )

        try:
            return self._llm.chat(system_prompt, question)
        except Exception:
            logger.error("LLM call failed for tax question")
            return (
                "I was able to retrieve your tax data, but the AI explanation is temporarily unavailable. "
                f"Here is your verified tax data:\n{verified_context}"
            )

    def _build_tax_context(self, calculation) -> str:
        """Build verified tax context string from persisted calculation."""
        return (
            f"TAX CALCULATION (verified, deterministic result):\n"
            f"- Tax Year: {calculation.tax_year}\n"
            f"- Rules Version: {calculation.rules_version}\n"
            f"- Total Income: £{calculation.total_income:,.2f}\n"
            f"- Personal Allowance / Total Allowances: £{calculation.total_allowances:,.2f}\n"
            f"- Taxable Income: £{calculation.taxable_income:,.2f}\n"
            f"- Income Tax Due: £{calculation.income_tax_due:,.2f}\n"
            f"- Assumptions: {calculation.assumptions}\n"
            f"- Limitations: {calculation.limitations}\n"
            f"- This is an estimate, NOT an official HMRC determination."
        )

    def _get_ai_explanation(self, verified_context: str) -> str:
        """Get AI explanation using verified tax context."""
        system_prompt = (
            f"{TAX_EXPLANATION_SYSTEM_PROMPT}\n\n"
            f"{verified_context}\n\n"
            f"Explain this tax calculation in clear, simple language. Cover:\n"
            f"1. How the tax was calculated\n"
            f"2. Which tax bands apply and why\n"
            f"3. The effective tax rate\n"
            f"4. Any important observations\n"
            f"5. Reminder that this is an estimate"
        )

        try:
            return self._llm.chat(system_prompt, "Please explain my tax calculation.")
        except Exception:
            logger.error("LLM call failed for tax explanation")
            return "AI explanation is temporarily unavailable. Please review the verified tax data directly."
