"""Financial Assistant - natural language orchestration across all finance capabilities."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.chat_llm import ChatLlm
from app.tools.financial_context_tools import get_full_financial_context

logger = logging.getLogger(__name__)

ASSISTANT_SYSTEM_PROMPT = """You are Finora, an AI-powered financial assistant. You help users understand and manage their personal finances.

You have access to the user's complete verified financial data. Use it to answer questions accurately.

RULES:
- ALL financial numbers in your response MUST come from the verified data provided.
- NEVER calculate, estimate, or invent any financial amounts.
- If you don't have enough information, say so.
- For tax questions, always remind users that estimates are not official HMRC determinations.
- Keep responses focused and actionable.
- All amounts are in GBP (£).
- You are not a replacement for a qualified financial advisor.

For UK Income Tax, the 2026/27 tax year rates apply: Personal Allowance £12,570, Basic Rate 20% (£12,571-£50,270), Higher Rate 40% (£50,271-£125,140), Additional Rate 45% (over £125,140).

CAPABILITIES:
- Summarize finances (income, expenses, net cash flow)
- Analyze budgets and spending patterns
- Explain tax calculations
- Identify spending trends
- Provide financial recommendations
"""


class FinancialAssistant:
    """Natural language orchestration across all finance capabilities.

    The assistant routes user questions to the appropriate domain-specific
    agent or retrieves verified data directly, then uses the LLM for
    natural language response generation.
    """

    def __init__(
        self,
        session: Session,
        llm: ChatLlm,
        budget_agent=None,
        report_agent=None,
        tax_agent=None,
    ) -> None:
        self._session = session
        self._llm = llm
        self._budget_agent = budget_agent
        self._report_agent = report_agent
        self._tax_agent = tax_agent

    def chat(
        self,
        user_id: UUID,
        user_name: str,
        message: str,
    ) -> str:
        """Process a user message and return a natural language response.

        Flow:
        1. Gather complete verified financial context (deterministic)
        2. Build system prompt with verified data
        3. AI generates response using ONLY verified context
        """
        context = get_full_financial_context(self._session, user_id, user_name)
        verified_data = self._build_context_string(context)

        system_prompt = (
            f"{ASSISTANT_SYSTEM_PROMPT}\n\n"
            f"USER FINANCIAL DATA:\n{verified_data}\n\n"
            f"Respond to the user's question using the verified data above."
        )

        return self._llm.chat(system_prompt, message)

    def _build_context_string(self, context) -> str:
        """Build verified financial context string from aggregated data."""
        lines = [
            f"User: {context.user_name}",
            f"---",
            f"TRANSACTION SUMMARY:",
            f"  Total transactions: {context.transactions.total_transactions}",
            f"  Total income: £{context.transactions.total_income:,.2f} ({context.transactions.income_count} transactions)",
            f"  Total expenses: £{context.transactions.total_expenses:,.2f} ({context.transactions.expense_count} transactions)",
            f"  Net: £{context.transactions.net_cash_flow:,.2f}",
        ]

        if context.transactions.top_categories:
            lines.append("  Top spending categories:")
            for cat in context.transactions.top_categories:
                lines.append(f"    - {cat['name']}: £{cat['total']:,.2f}")

        lines.append(f"\nBUDGET SUMMARY:")
        if context.budgets.budgets:
            for b in context.budgets.budgets:
                lines.append(
                    f"  - {b['category']}: £{b['budget_amount']:.2f} budgeted, "
                    f"£{b['actual_spending']:.2f} spent ({b['percentage_used']:.1%}), "
                    f"Status: {b['status']}"
                )
        else:
            lines.append("  No budgets set up.")

        lines.append(f"\nTAX SUMMARY:")
        if context.tax.latest_calculation:
            t = context.tax.latest_calculation
            lines.append(f"  Latest calculation ({t['tax_year']}):")
            lines.append(f"    Income: £{t['total_income']:,.2f}")
            lines.append(f"    Allowances: £{t['total_allowances']:,.2f}")
            lines.append(f"    Taxable: £{t['taxable_income']:,.2f}")
            lines.append(f"    Tax Due: £{t['income_tax_due']:,.2f}")
            lines.append(f"    Note: This is an estimate, NOT an official HMRC determination.")
        else:
            lines.append("  No tax calculations yet.")

        return "\n".join(lines)
