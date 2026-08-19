"""Budget Agent for hybrid deterministic budget analysis with AI reasoning."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.chat_llm import ChatLlm
from app.tools.budget_tools import (
    BudgetSpendingData,
    get_all_budgets_with_spending,
    get_budget_spending_detail,
)

logger = logging.getLogger(__name__)

BUDGET_ANALYSIS_SYSTEM_PROMPT = """You are Finora's Budget Analyst AI. You analyze the user's verified budget data and provide clear, actionable insights.

RULES:
- ALL financial numbers in your response MUST come from the verified data provided below.
- NEVER calculate, estimate, or invent any financial amounts.
- The budget_amount, actual_spending, percentage_used, remaining, and status values are authoritative.
- If the data shows a budget is "over_budget", state that fact with the exact numbers from the data.
- Provide specific, actionable recommendations based on the actual spending patterns.
- Be concise and direct. Focus on the most important observations first.
- All amounts are in GBP (£).
- You are not a replacement for a qualified financial advisor.
"""


class BudgetAgent:
    """Hybrid agent combining deterministic budget calculations with AI reasoning."""

    def __init__(self, session: Session, llm: ChatLlm) -> None:
        self._session = session
        self._llm = llm

    def analyze_budget(
        self,
        user_id: UUID,
        budget_id: UUID,
    ) -> dict:
        """Analyze a specific budget. Returns verified data + AI explanation."""
        budget_data = get_budget_spending_detail(self._session, user_id, budget_id)
        if budget_data is None:
            return {"error": "Budget not found or access denied."}

        verified_context = self._build_budget_context([budget_data])
        ai_explanation = self._get_ai_analysis(verified_context)

        return {
            "budget_data": {
                "category": budget_data.category_name,
                "budget_amount": budget_data.budget_amount,
                "actual_spending": budget_data.actual_spending,
                "remaining": budget_data.remaining,
                "percentage_used": budget_data.percentage_used,
                "status": budget_data.status,
                "transaction_count": budget_data.transaction_count,
                "period_start": budget_data.period_start,
                "period_end": budget_data.period_end,
            },
            "ai_analysis": ai_explanation,
        }

    def analyze_all_budgets(self, user_id: UUID) -> dict:
        """Analyze all budgets for a user. Returns verified data + AI summary."""
        budgets = get_all_budgets_with_spending(self._session, user_id)
        if not budgets:
            return {
                "budgets": [],
                "ai_summary": "You have no budgets set up yet. Consider creating budgets for your main spending categories to track your spending against limits.",
            }

        verified_context = self._build_budget_context(budgets)
        ai_summary = self._get_ai_analysis(verified_context)

        return {
            "budgets": [
                {
                    "category": b.category_name,
                    "budget_amount": b.budget_amount,
                    "actual_spending": b.actual_spending,
                    "remaining": b.remaining,
                    "percentage_used": b.percentage_used,
                    "status": b.status,
                }
                for b in budgets
            ],
            "ai_summary": ai_summary,
        }

    def answer_budget_question(
        self,
        user_id: UUID,
        question: str,
    ) -> str:
        """Answer a natural language question about the user's budgets.

        Flow:
        1. Deterministically gather ALL budget data
        2. Create verified financial context
        3. AI answers using ONLY the verified context
        """
        budgets = get_all_budgets_with_spending(self._session, user_id)
        verified_context = self._build_budget_context(budgets)

        system_prompt = (
            f"{BUDGET_ANALYSIS_SYSTEM_PROMPT}\n\n"
            f"VERIFIED BUDGET DATA:\n{verified_context}\n\n"
            f"Answer the user's question using ONLY the verified data above. "
            f"If the data does not contain enough information to answer, say so."
        )

        try:
            return self._llm.chat(system_prompt, question)
        except Exception:
            logger.error("LLM call failed for budget question")
            return (
                "I was able to retrieve your budget data, but the AI analysis is temporarily unavailable. "
                f"Here is your verified budget data:\n{verified_context}"
            )

    def _build_budget_context(self, budgets: list[BudgetSpendingData]) -> str:
        """Build verified financial context string from deterministic data."""
        if not budgets:
            return "No budgets found for this user."

        lines = ["VERIFIED BUDGET DATA (all numbers are from backend calculations):"]
        for b in budgets:
            lines.append(
                f"- {b.category_name}: £{b.budget_amount:.2f} budgeted, "
                f"£{b.actual_spending:.2f} spent ({b.percentage_used:.1%}), "
                f"£{b.remaining:.2f} remaining, "
                f"Status: {b.status}, "
                f"Transactions: {b.transaction_count}, "
                f"Period: {b.period_start} to {b.period_end}"
            )
        return "\n".join(lines)

    def _get_ai_analysis(self, verified_context: str) -> str:
        """Get AI analysis using verified budget context."""
        user_message = "Analyze my budget data. Provide a clear summary of my budget health, highlight any concerns, and give actionable recommendations."

        system_prompt = (
            f"{BUDGET_ANALYSIS_SYSTEM_PROMPT}\n\n"
            f"{verified_context}\n\n"
            f"Provide a comprehensive but concise budget analysis."
        )

        try:
            return self._llm.chat(system_prompt, user_message)
        except Exception:
            logger.error("LLM call failed for budget analysis")
            return "AI analysis is temporarily unavailable. Please review the verified budget data directly."
