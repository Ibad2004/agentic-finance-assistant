"""Tests for the Tax Agent AI explanation capability."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_user(prefix: str = "tax_ai") -> dict[str, str]:
    """Register a user and return auth headers."""
    email = f"{prefix}_{uuid4().hex[:8]}@example.com"
    password = "TaxAITest123!"
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_tax_calculation(headers: dict, income: str = "50000.00") -> dict:
    """Create a tax calculation and return the response."""
    res = client.post(
        "/tax/estimate",
        headers=headers,
        json={"total_income": income},
    )
    assert res.status_code == 200
    return res.json()


# --- TAX EXPLAIN ENDPOINT TESTS ---

def test_tax_explain_requires_auth() -> None:
    response = client.post(f"/tax/explain/{uuid4()}")
    assert response.status_code == 401


def test_tax_explain_nonexistent_calculation_returns_404() -> None:
    headers = register_user("te_notfound")
    response = client.post(f"/tax/explain/{uuid4()}", headers=headers)
    assert response.status_code == 404


def test_tax_explain_with_valid_calculation() -> None:
    headers = register_user("te_valid")
    calc = create_tax_calculation(headers, "50000.00")
    calc_id = calc["id"]

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "Your tax is £7,486.00 because you're in the basic rate band."
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(f"/tax/explain/{calc_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    # Verify the LLM received verified tax data
    system_prompt = mock_llm.chat.call_args[0][0]
    assert "50,000.00" in system_prompt
    assert "7,486.00" in system_prompt
    assert "estimate" in system_prompt.lower() or "hmrc" in system_prompt.lower()


def test_tax_explain_llm_failure_returns_fallback() -> None:
    headers = register_user("te_fail")
    calc = create_tax_calculation(headers, "50000.00")
    calc_id = calc["id"]

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.side_effect = Exception("Groq API timeout")
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(f"/tax/explain/{calc_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "unavailable" in data["response"].lower() or "review" in data["response"].lower()


def test_tax_explain_llm_not_configured_returns_503() -> None:
    headers = register_user("te_noconfig")
    calc = create_tax_calculation(headers, "50000.00")
    calc_id = calc["id"]

    with patch("app.services.groq_chat_llm.GroqChatLlm", side_effect=RuntimeError("Groq is not configured.")):
        response = client.post(f"/tax/explain/{calc_id}", headers=headers)

    assert response.status_code == 503


def test_tax_explain_user_isolation() -> None:
    """Verify that one user cannot explain another user's tax calculation."""
    headers_a = register_user("te_iso_a")
    headers_b = register_user("te_iso_b")
    calc = create_tax_calculation(headers_a, "50000.00")
    calc_id = calc["id"]

    # User B tries to explain User A's calculation
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "Explanation"
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(f"/tax/explain/{calc_id}", headers=headers_b)

    assert response.status_code == 404


# --- TAX CHAT ENDPOINT TESTS ---

def test_tax_chat_requires_auth() -> None:
    response = client.post("/tax/chat", json={"question": "Why is my tax high?"})
    assert response.status_code == 401


def test_tax_chat_no_calculations_returns_message() -> None:
    headers = register_user("tc_nocalc")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "You have no tax calculations yet."
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/tax/chat",
            headers=headers,
            json={"question": "Explain my tax"},
        )
    assert response.status_code == 200


def test_tax_chat_with_calculation() -> None:
    headers = register_user("tc_calc")
    create_tax_calculation(headers, "50000.00")

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "You're in the basic rate band."
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/tax/chat",
            headers=headers,
            json={"question": "Why is my tax so high?"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


def test_tax_chat_llm_failure_returns_fallback() -> None:
    headers = register_user("tc_fail")
    create_tax_calculation(headers, "50000.00")

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.side_effect = Exception("LLM error")
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/tax/chat",
            headers=headers,
            json={"question": "Explain my tax"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "unavailable" in data["response"].lower() or "verified" in data["response"].lower()


def test_tax_chat_llm_not_configured_returns_503() -> None:
    headers = register_user("tc_noconfig")
    with patch("app.services.groq_chat_llm.GroqChatLlm", side_effect=RuntimeError("Groq is not configured.")):
        response = client.post(
            "/tax/chat",
            headers=headers,
            json={"question": "Hello"},
        )
    assert response.status_code == 503


# --- DETERMINISTIC INTEGRITY TESTS ---

def test_tax_calculation_deterministic_values_unchanged() -> None:
    """Verify that the tax calculation engine produces the same results as before."""
    headers = register_user("te_det")
    calc = create_tax_calculation(headers, "50000.00")
    # These values must come from the deterministic tax engine
    assert calc["total_income"] == 50000.0
    assert calc["taxable_income"] == 37430.0
    assert calc["income_tax_due"] == 7486.0
    assert calc["tax_year"] == "2026/27"


def test_tax_explain_does_not_override_calculation() -> None:
    """Verify that the AI explanation does not change the tax calculation."""
    headers = register_user("te_override")
    calc_before = create_tax_calculation(headers, "50000.00")
    calc_id = calc_before["id"]

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "Your tax should be £5,000."  # AI trying to override
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        client.post(f"/tax/explain/{calc_id}", headers=headers)

    # Verify the calculation is unchanged
    res = client.get(f"/tax/calculations/{calc_id}", headers=headers)
    assert res.status_code == 200
    calc_after = res.json()
    assert calc_after["income_tax_due"] == 7486.0  # Still the deterministic value
    assert calc_after["total_income"] == 50000.0


def test_tax_explain_context_contains_disclaimer() -> None:
    """Verify that the AI context includes the HMRC disclaimer."""
    headers = register_user("te_disclaimer")
    calc = create_tax_calculation(headers, "50000.00")
    calc_id = calc["id"]

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "OK"
    with patch("app.services.groq_chat_llm.GroqChatLlm", return_value=mock_llm):
        client.post(f"/tax/explain/{calc_id}", headers=headers)

    system_prompt = mock_llm.chat.call_args[0][0]
    assert "estimate" in system_prompt.lower()
    assert "hmrc" in system_prompt.lower() or "official" in system_prompt.lower()


def test_tax_band_breakdown_is_deterministic() -> None:
    """Verify that tax band breakdown comes from the engine, not AI."""
    headers = register_user("te_bands")
    calc = create_tax_calculation(headers, "150000.00")
    # For £150,000 income:
    # Personal Allowance: tapered to £0 (income > £125,140)
    # Taxable: £150,000
    # Basic: £37,700 * 20% = £7,540
    # Higher: (£125,140 - £37,700) * 40% = £87,440 * 40% = £34,976
    # Additional: (£150,000 - £125,140) * 45% = £24,860 * 45% = £11,187
    # Total: £7,540 + £34,976 + £11,187 = £53,703
    assert calc["income_tax_due"] == 53703.0
    assert calc["total_allowances"] == 0.0
    assert calc["taxable_income"] == 150000.0
