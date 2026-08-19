"""Report Agent for hybrid deterministic financial reporting with AI insights."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.chat_llm import ChatLlm
from app.tools.report_tools import (
    FinancialSummaryData,
    get_financial_summary,
    get_top_transactions,
)

logger = logging.getLogger(__name__)

REPORT_INSIGHTS_SYSTEM_PROMPT = """You are Finora's Financial Report Analyst AI. You analyze verified financial data and provide clear, actionable insights.

RULES:
- ALL financial numbers in your response MUST come from the verified data provided.
- NEVER calculate, estimate, or invent any financial amounts.
- The total_income, total_expenses, net_cash_flow, and category_breakdown are authoritative.
- Identify the most significant observations from the data.
- Provide actionable insights based on actual spending patterns.
- Be concise and executive-focused. Lead with the most important finding.
- All amounts are in GBP (£).
- You are not a replacement for a qualified financial advisor.
"""


class ReportAgent:
    """Hybrid agent combining deterministic financial reporting with AI insights."""

    def __init__(self, session: Session, llm: ChatLlm) -> None:
        self._session = session
        self._llm = llm

    def generate_insights(
        self,
        user_id: UUID,
        period_start,
        period_end,
    ) -> dict:
        """Generate AI insights for a financial period.

        Flow:
        1. Deterministically gather ALL financial data for the period
        2. Gather top transactions
        3. Create verified financial context
        4. AI generates insights using ONLY verified data

        The AI does NOT invent numbers. It only provides commentary on verified data.
        """
        summary = get_financial_summary(self._session, user_id, period_start, period_end)
        top_txns = get_top_transactions(self._session, user_id, period_start, period_end)

        verified_context = self._build_report_context(summary, top_txns)
        ai_insights = self._get_ai_insights(verified_context)

        return {
            "report_data": {
                "total_income": summary.total_income,
                "total_expenses": summary.total_expenses,
                "net_cash_flow": summary.net_cash_flow,
                "transaction_count": summary.transaction_count,
                "category_breakdown": summary.category_breakdown,
                "period_start": summary.period_start,
                "period_end": summary.period_end,
            },
            "ai_insights": ai_insights,
        }

    def answer_report_question(
        self,
        user_id: UUID,
        question: str,
        period_start,
        period_end,
    ) -> str:
        """Answer a natural language question about the user's financial report."""
        summary = get_financial_summary(self._session, user_id, period_start, period_end)
        top_txns = get_top_transactions(self._session, user_id, period_start, period_end)
        verified_context = self._build_report_context(summary, top_txns)

        system_prompt = (
            f"{REPORT_INSIGHTS_SYSTEM_PROMPT}\n\n"
            f"VERIFIED FINANCIAL DATA:\n{verified_context}\n\n"
            f"Answer the user's question using ONLY the verified data above. "
            f"If the data does not contain enough information, say so."
        )

        try:
            return self._llm.chat(system_prompt, question)
        except Exception:
            logger.error("LLM call failed for report question")
            return (
                "I was able to retrieve your financial data, but the AI analysis is temporarily unavailable. "
                f"Here is your verified financial data:\n{verified_context}"
            )

    def _build_report_context(
        self,
        summary: FinancialSummaryData,
        top_txns: list[dict],
    ) -> str:
        """Build verified financial context string from deterministic data."""
        lines = [
            "VERIFIED FINANCIAL REPORT DATA (all numbers from backend calculations):",
            f"Period: {summary.period_start} to {summary.period_end}",
            f"Total Income: £{summary.total_income:,.2f} ({summary.income_count} transactions)",
            f"Total Expenses: £{summary.total_expenses:,.2f} ({summary.expense_count} transactions)",
            f"Net Cash Flow: £{summary.net_cash_flow:,.2f}",
            f"Total Transactions: {summary.transaction_count}",
        ]

        if summary.category_breakdown:
            lines.append("\nEXPENSE BREAKDOWN BY CATEGORY:")
            for category, amount in summary.category_breakdown.items():
                lines.append(f"  - {category}: £{amount:,.2f}")

        if top_txns:
            lines.append("\nTOP EXPENSES:")
            for tx in top_txns:
                lines.append(f"  - {tx['description']}: £{tx['amount']:,.2f} on {tx['date']}")

        return "\n".join(lines)

    def _get_ai_insights(self, verified_context: str) -> str:
        """Get AI insights using verified financial context."""
        system_prompt = (
            f"{REPORT_INSIGHTS_SYSTEM_PROMPT}\n\n"
            f"{verified_context}\n\n"
            f"Provide an executive-style financial summary covering:\n"
            f"1. Overall financial performance\n"
            f"2. Key spending patterns\n"
            f"3. Most significant observations\n"
            f"4. Actionable recommendations"
        )

        try:
            return self._llm.chat(system_prompt, "Analyze my financial report.")
        except Exception:
            logger.error("LLM call failed for report insights")
            return "AI insights are temporarily unavailable. Please review the verified financial data directly."
