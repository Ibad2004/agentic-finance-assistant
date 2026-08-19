"""Tests for the Budget Agent hybrid AI architecture."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

LLM_PATH = "app.services.groq_chat_llm.GroqChatLlm"


def register_user(prefix: str = "budget_agent") -> dict[str, str]:
    """Register a user and return auth headers."""
    email = f"{prefix}_{uuid4().hex[:8]}@example.com"
    password = "BudgetAgentTest123!"
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def get_food_category_id() -> str:
    from app.db.session import SessionLocal
    from app.db.models import TransactionCategory
    db = SessionLocal()
    try:
        cat = db.query(TransactionCategory).filter_by(name="Food").first()
        assert cat is not None
        return str(cat.id)
    finally:
        db.close()


def create_account(headers: dict) -> str:
    res = client.post(
        "/accounts",
        headers=headers,
        json={"account_name": "Budget Agent Test Account", "account_type": "current", "currency_code": "GBP"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_budget(headers: dict, category_id: str, amount: str, start: str, end: str) -> dict:
    res = client.post(
        "/budgets",
        headers=headers,
        json={"category_id": category_id, "budget_amount": amount, "period_start": start, "period_end": end},
    )
    return res


def import_transactions(headers: dict, account_id: str, csv_content: bytes) -> None:
    res = client.post(
        f"/accounts/{account_id}/transactions/import",
        headers=headers,
        files={"file": ("test.csv", BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 200


def categorize_transactions(headers: dict, account_id: str) -> None:
    mock_llm = MagicMock()
    mock_llm.categorize_batch.return_value = None
    with patch("app.agents.transaction_agent.GroqTransactionCategorizationLlm", return_value=mock_llm):
        client.post(f"/accounts/{account_id}/transactions/categorize", headers=headers)


# --- BUDGET ANALYSIS ENDPOINT TESTS ---

def test_budget_analyze_requires_auth() -> None:
    response = client.post("/budgets/analyze")
    assert response.status_code == 401


def test_budget_analyze_no_budgets_returns_summary() -> None:
    headers = register_user("ba_empty")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "You have no budgets yet."
    with patch(LLM_PATH, return_value=mock_llm):
        response = client.post("/budgets/analyze", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


def test_budget_analyze_with_budgets_returns_verified_data() -> None:
    headers = register_user("ba_with")
    food_id = get_food_category_id()
    create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "Your food budget is under control."
    with patch(LLM_PATH, return_value=mock_llm):
        response = client.post("/budgets/analyze", headers=headers)
    assert response.status_code == 200
    system_prompt = mock_llm.chat.call_args[0][0]
    assert "Food" in system_prompt
    assert "500.00" in system_prompt


def test_budget_analyze_llm_failure_graceful_fallback() -> None:
    """Agent catches LLM errors internally; route returns 200 with fallback text."""
    headers = register_user("ba_fail")
    food_id = get_food_category_id()
    create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.side_effect = Exception("Groq API timeout")
    with patch(LLM_PATH, return_value=mock_llm):
        response = client.post("/budgets/analyze", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "unavailable" in data["response"].lower() or "temporarily" in data["response"].lower()


# --- BUDGET CHAT ENDPOINT TESTS ---

def test_budget_chat_requires_auth() -> None:
    response = client.post("/budgets/chat", json={"message": "How am I doing?"})
    assert response.status_code == 401


def test_budget_chat_with_empty_message_returns_422() -> None:
    headers = register_user("bc_empty")
    response = client.post("/budgets/chat", headers=headers, json={"message": ""})
    assert response.status_code == 422


def test_budget_chat_returns_ai_response() -> None:
    headers = register_user("bc_ok")
    food_id = get_food_category_id()
    create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "You've used 0% of your £500 food budget."
    with patch(LLM_PATH, return_value=mock_llm):
        response = client.post(
            "/budgets/chat",
            headers=headers,
            json={"message": "How is my food budget?"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    system_prompt = mock_llm.chat.call_args[0][0]
    assert "Food" in system_prompt
    assert "500.00" in system_prompt


def test_budget_chat_llm_failure_graceful_fallback() -> None:
    """Agent catches LLM errors internally; route returns 200 with fallback text."""
    headers = register_user("bc_fail")
    food_id = get_food_category_id()
    create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.side_effect = Exception("LLM error")
    with patch(LLM_PATH, return_value=mock_llm):
        response = client.post(
            "/budgets/chat",
            headers=headers,
            json={"message": "Analyze my spending"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "unavailable" in data["response"].lower() or "temporarily" in data["response"].lower()


def test_budget_chat_llm_not_configured_returns_503() -> None:
    headers = register_user("bc_noconfig")
    with patch(LLM_PATH, side_effect=RuntimeError("Groq is not configured.")):
        response = client.post(
            "/budgets/chat",
            headers=headers,
            json={"message": "Hello"},
        )
    assert response.status_code == 503


# --- DETERMINISTIC INTEGRITY TESTS ---

def test_budget_deterministic_values_not_changed_by_ai() -> None:
    """Verify that budget CRUD returns deterministic values regardless of AI."""
    headers = register_user("ba_det")
    food_id = get_food_category_id()
    create_res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = create_res.json()
    assert data["budget_amount"] == 500.0
    assert data["actual_spending"] == 0.0
    assert data["remaining"] == 500.0
    assert data["percentage_used"] == 0.0
    assert data["status"] == "under_budget"
    assert data["transaction_count"] == 0


def test_budget_spending_aggregation_remains_deterministic() -> None:
    """Verify that spending aggregation is deterministic even with AI analysis."""
    headers = register_user("ba_spend_det")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    csv = b"transaction_date,description,debit,credit,balance,reference,currency\n2026-04-10,TESCO,100.00,,400.00,T1,GBP\n"
    import_transactions(headers, account_id, csv)
    categorize_transactions(headers, account_id)

    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["actual_spending"] == 100.0
    assert data["percentage_used"] == 0.2
    assert data["remaining"] == 400.0
    assert data["status"] == "under_budget"


def test_budget_percentage_calculation_is_deterministic() -> None:
    """Verify percentage calculation uses Decimal arithmetic, not AI."""
    headers = register_user("ba_pct_det")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    csv = b"transaction_date,description,debit,credit,balance,reference,currency\n2026-04-10,TESCO,450.00,,50.00,T1,GBP\n"
    import_transactions(headers, account_id, csv)
    categorize_transactions(headers, account_id)

    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["percentage_used"] == 0.9
    assert data["status"] == "near_limit"


def test_budget_over_budget_status_is_deterministic() -> None:
    """Verify over_budget status is determined by backend, not AI."""
    headers = register_user("ba_over_det")
    food_id = get_food_category_id()
    account_id = create_account(headers)
    csv = b"transaction_date,description,debit,credit,balance,reference,currency\n2026-04-10,TESCO,600.00,,-100.00,T1,GBP\n"
    import_transactions(headers, account_id, csv)
    categorize_transactions(headers, account_id)

    res = create_budget(headers, food_id, "500.00", "2026-04-01", "2026-04-30")
    data = res.json()
    assert data["actual_spending"] == 600.0
    assert data["remaining"] == -100.0
    assert data["status"] == "over_budget"


# --- USER ISOLATION TESTS ---

def test_budget_analysis_user_isolation() -> None:
    """Verify that budget analysis only sees the authenticated user's budgets."""
    headers_a = register_user("ba_iso_a")
    headers_b = register_user("ba_iso_b")
    food_id = get_food_category_id()
    create_budget(headers_a, food_id, "500.00", "2026-04-01", "2026-04-30")
    create_budget(headers_b, food_id, "300.00", "2026-04-01", "2026-04-30")

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "OK"
    with patch(LLM_PATH, return_value=mock_llm):
        res_a = client.post("/budgets/analyze", headers=headers_a)
        res_b = client.post("/budgets/analyze", headers=headers_b)

    assert res_a.status_code == 200
    assert res_b.status_code == 200
    prompt_a = mock_llm.chat.call_args_list[-2][0][0]
    prompt_b = mock_llm.chat.call_args_list[-1][0][0]
    assert "500.00" in prompt_a
    assert "300.00" in prompt_b
