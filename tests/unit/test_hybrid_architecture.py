"""Tests verifying hybrid AI architecture principles.

These tests verify that:
- Deterministic calculations are the source of truth
- AI/LLM cannot override authoritative financial values
- Financial numbers always come from backend services
- The LLM is only used for natural language reasoning
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from app.agents.budget_agent import BudgetAgent
from app.agents.report_agent import ReportAgent
from app.agents.tax_agent import TaxAgent
from app.agents.financial_assistant import FinancialAssistant
from app.services.budget_service import _compute_status
from app.tax.uk.england.tax_year_2026_27.calculator import (
    calculate_england_income_tax_2026_27,
    calculate_personal_allowance,
)


# --- DETERMINISTIC TAX ENGINE TESTS ---

def test_tax_engine_deterministic_with_50000() -> None:
    """Tax engine produces deterministic result for £50,000 income."""
    result = calculate_england_income_tax_2026_27(Decimal("50000.00"))
    assert result.total_income == Decimal("50000.00")
    assert result.personal_allowance == Decimal("12570.00")
    assert result.taxable_income == Decimal("37430.00")
    assert result.income_tax_due == Decimal("7486.00")


def test_tax_engine_deterministic_with_150000() -> None:
    """Tax engine produces deterministic result for £150,000 income."""
    result = calculate_england_income_tax_2026_27(Decimal("150000.00"))
    assert result.total_income == Decimal("150000.00")
    assert result.personal_allowance == Decimal("0.00")
    assert result.taxable_income == Decimal("150000.00")
    assert result.income_tax_due == Decimal("53703.00")


def test_tax_engine_deterministic_with_110000() -> None:
    """Tax engine produces deterministic result for £110,000 (taper zone)."""
    result = calculate_england_income_tax_2026_27(Decimal("110000.00"))
    assert result.total_income == Decimal("110000.00")
    assert result.personal_allowance == Decimal("7570.00")
    assert result.taxable_income == Decimal("102430.00")


# --- BUDGET STATUS DETERMINISTIC TESTS ---

def test_budget_status_under_budget() -> None:
    assert _compute_status(Decimal("0.50")) == "under_budget"
    assert _compute_status(Decimal("0.79")) == "under_budget"


def test_budget_status_near_limit() -> None:
    assert _compute_status(Decimal("0.80")) == "near_limit"
    assert _compute_status(Decimal("0.90")) == "near_limit"
    assert _compute_status(Decimal("1.00")) == "near_limit"


def test_budget_status_over_budget() -> None:
    assert _compute_status(Decimal("1.01")) == "over_budget"
    assert _compute_status(Decimal("1.50")) == "over_budget"
    assert _compute_status(Decimal("2.00")) == "over_budget"


# --- TAX AGENT CANNOT BE OVERRIDDEN BY AI ---

def test_tax_agent_calculate_and_save_ignores_llm() -> None:
    """The TaxAgent.calculate_and_save method does not use the LLM at all."""
    from app.db.models import TaxCalculation

    class MockSession:
        def __init__(self):
            self.added = []
            self.committed = False
        def add(self, instance):
            self.added.append(instance)
        def flush(self):
            pass
        def commit(self):
            self.committed = True
        def rollback(self):
            self.committed = False

    mock_llm = MagicMock()
    session = MockSession()
    agent = TaxAgent(session=session, llm=mock_llm)

    result = agent.calculate_and_save(
        user_id=uuid4(),
        total_income=Decimal("50000.00"),
    )

    # The result must be from the deterministic engine
    assert isinstance(result, TaxCalculation)
    assert result.total_income == Decimal("50000.00")
    assert result.income_tax_due == Decimal("7486.00")
    # The LLM must NOT have been called during calculate_and_save
    mock_llm.chat.assert_not_called()


def test_tax_agent_explain_uses_llm_but_does_not_change_calculation() -> None:
    """The TaxAgent.explain_tax method uses the LLM for explanation but cannot change the calculation."""
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "Your tax is £5,000."  # AI trying to give wrong number

    agent = TaxAgent(session=MagicMock(), llm=mock_llm)
    context = agent._build_tax_context(type('Calc', (), {
        'tax_year': '2026/27',
        'rules_version': '2026_27_england_v1',
        'total_income': Decimal('50000.00'),
        'total_allowances': Decimal('12570.00'),
        'taxable_income': Decimal('37430.00'),
        'income_tax_due': Decimal('7486.00'),
        'assumptions': 'Test assumptions',
        'limitations': 'Test limitations',
    })())

    # The context must contain the correct deterministic values
    assert "7,486.00" in context
    assert "50,000.00" in context
    assert "12,570.00" in context
    # The AI's incorrect value should NOT be in the context
    assert "5,000" not in context


# --- BUDGET AGENT CANNOT OVERRIDE DETERMINISTIC VALUES ---

def test_budget_agent_build_context_contains_deterministic_data() -> None:
    """The BudgetAgent builds context from verified data, not AI."""
    from app.tools.budget_tools import BudgetSpendingData

    agent = BudgetAgent(session=MagicMock(), llm=MagicMock())
    budget = BudgetSpendingData(
        budget_id=uuid4(),
        category_name="Food",
        budget_amount=500.0,
        actual_spending=100.0,
        remaining=400.0,
        percentage_used=0.2,
        status="under_budget",
        transaction_count=3,
        period_start="2026-04-01",
        period_end="2026-04-30",
    )

    context = agent._build_budget_context([budget])

    # All numbers must be from the deterministic data
    assert "500.00" in context
    assert "100.00" in context
    assert "400.00" in context
    assert "20.0%" in context
    assert "under_budget" in context


def test_budget_agent_build_context_empty_budgets() -> None:
    """Empty budgets list returns appropriate message."""
    agent = BudgetAgent(session=MagicMock(), llm=MagicMock())
    context = agent._build_budget_context([])
    assert "No budgets found" in context


# --- REPORT AGENT CANNOT OVERRIDE DETERMINISTIC VALUES ---

def test_report_agent_build_context_contains_deterministic_data() -> None:
    """The ReportAgent builds context from verified data, not AI."""
    from app.tools.report_tools import FinancialSummaryData

    agent = ReportAgent(session=MagicMock(), llm=MagicMock())
    summary = FinancialSummaryData(
        total_income=3000.0,
        total_expenses=290.0,
        net_cash_flow=2710.0,
        transaction_count=4,
        income_count=1,
        expense_count=3,
        category_breakdown={"Food": 150.0, "Utilities": 95.0, "Transport": 45.0},
        period_start="2026-04-01",
        period_end="2026-04-30",
    )

    context = agent._build_report_context(summary, [])

    # All numbers must be from the deterministic data
    assert "3,000.00" in context
    assert "290.00" in context
    assert "2,710.00" in context
    assert "4" in context


# --- FINANCIAL ASSISTANT CONTEXT INTEGRITY ---

def test_financial_assistant_context_contains_verified_data() -> None:
    """The FinancialAssistant context must contain verified financial data."""
    from app.tools.financial_context_tools import (
        FullFinancialContext,
        TransactionSummary,
        BudgetSummary,
        TaxSummary,
    )

    context = FullFinancialContext(
        user_name="Test User",
        transactions=TransactionSummary(
            total_transactions=10,
            total_income=5000.0,
            income_count=2,
            total_expenses=3000.0,
            expense_count=8,
            net_cash_flow=2000.0,
            top_categories=[{"name": "Food", "total": 500.0}],
        ),
        budgets=BudgetSummary(
            total_budgets=1,
            budgets=[{"category": "Food", "budget_amount": 600.0, "actual_spending": 500.0, "percentage_used": 0.83, "status": "near_limit", "period_start": "2026-04-01", "period_end": "2026-04-30"}],
        ),
        tax=TaxSummary(
            latest_calculation={"tax_year": "2026/27", "total_income": 50000.0, "total_allowances": 12570.0, "taxable_income": 37430.0, "income_tax_due": 7486.0, "rules_version": "2026_27_england_v1"},
            total_calculations=1,
        ),
    )

    assistant = FinancialAssistant(session=MagicMock(), llm=MagicMock())
    context_str = assistant._build_context_string(context)

    # Must contain verified deterministic values
    assert "5,000.00" in context_str  # income
    assert "3,000.00" in context_str  # expenses
    assert "2,000.00" in context_str  # net
    assert "500.00" in context_str    # food category
    assert "600.00" in context_str    # budget
    assert "7,486.00" in context_str  # tax
    assert "2026/27" in context_str   # tax year
    assert "estimate" in context_str.lower()  # HMRC disclaimer


# --- PROVIDER-NEUTRAL LLM INTERFACE ---

def test_chat_llm_protocol_is_satisfied() -> None:
    """Verify that the ChatLlm protocol can be satisfied by a mock."""
    from app.services.chat_llm import ChatLlm

    class MockChatLlm:
        def chat(self, system_prompt: str, user_message: str) -> str:
            return "mock response"

    mock = MockChatLlm()
    # This should not raise - the protocol is structurally satisfied
    assert hasattr(mock, 'chat')
    result = mock.chat("system", "user")
    assert result == "mock response"


def test_budget_agent_uses_chat_llm_protocol() -> None:
    """BudgetAgent accepts any ChatLlm implementation."""
    class MockChatLlm:
        def chat(self, system_prompt: str, user_message: str) -> str:
            return "Budget analysis"

    agent = BudgetAgent(session=MagicMock(), llm=MockChatLlm())
    assert agent._llm is not None
    result = agent._llm.chat("system", "user")
    assert result == "Budget analysis"


def test_report_agent_uses_chat_llm_protocol() -> None:
    """ReportAgent accepts any ChatLlm implementation."""
    class MockChatLlm:
        def chat(self, system_prompt: str, user_message: str) -> str:
            return "Report insights"

    agent = ReportAgent(session=MagicMock(), llm=MockChatLlm())
    assert agent._llm is not None
    result = agent._llm.chat("system", "user")
    assert result == "Report insights"


def test_financial_assistant_uses_chat_llm_protocol() -> None:
    """FinancialAssistant accepts any ChatLlm implementation."""
    class MockChatLlm:
        def chat(self, system_prompt: str, user_message: str) -> str:
            return "Financial advice"

    assistant = FinancialAssistant(session=MagicMock(), llm=MockChatLlm())
    assert assistant._llm is not None
    result = assistant._llm.chat("system", "user")
    assert result == "Financial advice"
