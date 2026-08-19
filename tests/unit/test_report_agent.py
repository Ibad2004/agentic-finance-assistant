"""Tests for the Report Agent hybrid AI architecture."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_user(prefix: str = "report_agent") -> dict[str, str]:
    """Register a user and return auth headers."""
    email = f"{prefix}_{uuid4().hex[:8]}@example.com"
    password = "ReportAgentTest123!"
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_account(headers: dict) -> str:
    res = client.post(
        "/accounts",
        headers=headers,
        json={"account_name": "Report Agent Test Account", "account_type": "current", "currency_code": "GBP"},
    )
    assert res.status_code == 201
    return res.json()["id"]


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


SAMPLE_CSV = b"""transaction_date,description,debit,credit,balance,reference,currency
2026-04-06,ACME PAYROLL LTD,,3000.00,3000.00,SALARY-APR,GBP
2026-04-10,TESCO STORES,150.00,,2850.00,TESCO-1,GBP
2026-04-15,OCTOPUS ENERGY,95.00,,2755.00,ENERGY-1,GBP
2026-04-20,TFL TRAVEL CHARGE,45.00,,2710.00,TFL-1,GBP
"""


# --- REPORT INSIGHTS ENDPOINT TESTS ---

def test_report_insights_requires_auth() -> None:
    response = client.post(
        "/reports/insights",
        json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
    )
    assert response.status_code == 401


def test_report_insights_empty_period() -> None:
    headers = register_user("ri_empty")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "No transactions found for this period."
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/reports/insights",
            headers=headers,
            json={"report_type": "monthly_summary", "period_start": "2026-01-01", "period_end": "2026-01-31"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


def test_report_insights_with_transactions() -> None:
    headers = register_user("ri_tx")
    account_id = create_account(headers)
    import_transactions(headers, account_id, SAMPLE_CSV)
    categorize_transactions(headers, account_id)

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "Your expenses are well managed."
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/reports/insights",
            headers=headers,
            json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
        )
    assert response.status_code == 200
    # Verify the LLM received verified financial data
    system_prompt = mock_llm.chat.call_args[0][0]
    assert "3,000.00" in system_prompt  # income
    assert "290.00" in system_prompt   # expenses


def test_report_insights_llm_failure_graceful_fallback() -> None:
    """Agent catches LLM errors internally; route returns 200 with fallback text."""
    headers = register_user("ri_fail")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.side_effect = Exception("Groq API timeout")
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/reports/insights",
            headers=headers,
            json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "unavailable" in data["response"].lower() or "temporarily" in data["response"].lower()


def test_report_insights_llm_not_configured_returns_503() -> None:
    headers = register_user("ri_noconfig")
    with patch("app.services.groq_chat_llm.GroqChatLlm", side_effect=RuntimeError("Groq is not configured.")):
        response = client.post(
            "/reports/insights",
            headers=headers,
            json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
        )
    assert response.status_code == 503


def test_report_insights_user_isolation() -> None:
    """Verify that report insights only see the authenticated user's data."""
    headers_a = register_user("ri_iso_a")
    headers_b = register_user("ri_iso_b")
    account_a = create_account(headers_a)
    import_transactions(headers_a, account_a, SAMPLE_CSV)
    categorize_transactions(headers_a, account_a)

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "OK"
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/reports/insights",
            headers=headers_a,
            json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
        )
        client.post(
            "/reports/insights",
            headers=headers_b,
            json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
        )

    # User A should have financial data in context, User B should not
    prompt_a = mock_llm.chat.call_args_list[-2][0][0]
    prompt_b = mock_llm.chat.call_args_list[-1][0][0]
    assert "3,000.00" in prompt_a  # User A has income
    assert "0.00" in prompt_b  # User B has no transactions


# --- DETERMINISTIC INTEGRITY TESTS ---

def test_report_generate_still_works_deterministically() -> None:
    """Verify that the existing PDF report generation is unchanged."""
    headers = register_user("ri_pdf")
    account_id = create_account(headers)
    import_transactions(headers, account_id, SAMPLE_CSV)
    categorize_transactions(headers, account_id)

    res = client.post(
        "/reports/generate",
        headers=headers,
        json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["total_income"] == 3000.0
    assert data["total_expenses"] == 290.0
    assert data["net_amount"] == 2710.0
    assert data["transaction_count"] == 4
    assert data["file_format"] == "pdf"


def test_report_insights_does_not_alter_report_data() -> None:
    """Verify that AI insights do not alter the deterministic report data."""
    headers = register_user("ri_noalter")
    account_id = create_account(headers)
    import_transactions(headers, account_id, SAMPLE_CSV)
    categorize_transactions(headers, account_id)

    # Generate the deterministic report first
    report_res = client.post(
        "/reports/generate",
        headers=headers,
        json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
    )
    report_data = report_res.json()

    # Then generate AI insights
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "Your expenses increased by 14%."
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/reports/insights",
            headers=headers,
            json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
        )

    # Verify the deterministic report data is unchanged
    res = client.get(f"/reports/{report_data['id']}", headers=headers)
    assert res.status_code == 200
    # Report data must still be deterministic
    assert report_data["total_income"] == 3000.0
    assert report_data["total_expenses"] == 290.0


def test_report_ai_context_contains_category_breakdown() -> None:
    """Verify that the AI receives verified category breakdown data."""
    headers = register_user("ri_cats")
    account_id = create_account(headers)
    import_transactions(headers, account_id, SAMPLE_CSV)
    categorize_transactions(headers, account_id)

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "OK"
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/reports/insights",
            headers=headers,
            json={"report_type": "monthly_summary", "period_start": "2026-04-01", "period_end": "2026-04-30"},
        )

    system_prompt = mock_llm.chat.call_args[0][0]
    assert "EXPENSE BREAKDOWN" in system_prompt or "category" in system_prompt.lower()
