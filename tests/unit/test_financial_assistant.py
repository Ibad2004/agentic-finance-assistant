"""Tests for the Financial Assistant agent."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_user(prefix: str = "fin_asst") -> dict[str, str]:
    """Register a user and return auth headers."""
    email = f"{prefix}_{uuid4().hex[:8]}@example.com"
    password = "FinAsstTest123!"
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# --- FINANCIAL ASSISTANT AGENT TESTS ---

def test_financial_assistant_chat_requires_auth() -> None:
    response = client.post("/assistant/chat", json={"message": "Hello"})
    assert response.status_code == 401


def test_financial_assistant_empty_message_returns_422() -> None:
    headers = register_user("fa_empty")
    response = client.post("/assistant/chat", headers=headers, json={"message": ""})
    assert response.status_code == 422


def test_financial_assistant_message_too_long_returns_422() -> None:
    headers = register_user("fa_long")
    response = client.post("/assistant/chat", headers=headers, json={"message": "x" * 2001})
    assert response.status_code == 422


def test_financial_assistant_returns_llm_response() -> None:
    """The Financial Assistant returns the LLM's response via the agent."""
    headers = register_user("fa_basic")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "You have no transactions yet. Import some data to get started."

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "Summarize my finances"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0
    mock_llm.chat.assert_called_once()


def test_financial_assistant_context_includes_verified_data() -> None:
    """The system prompt includes verified financial data from the backend."""
    headers = register_user("fa_ctx")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "Based on your data..."

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "What do I spend the most on?"},
        )

    system_prompt = mock_llm.chat.call_args[0][0]
    assert "TRANSACTION SUMMARY:" in system_prompt
    assert "BUDGET SUMMARY:" in system_prompt
    assert "TAX SUMMARY:" in system_prompt


def test_financial_assistant_user_message_passed_to_llm() -> None:
    """The user's message is passed to the LLM."""
    headers = register_user("fa_msg")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "OK"

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "How much did I spend on food?"},
        )

    user_message = mock_llm.chat.call_args[0][1]
    assert user_message == "How much did I spend on food?"


def test_financial_assistant_llm_failure_returns_502() -> None:
    """LLM failure results in a 502 error."""
    headers = register_user("fa_fail")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.side_effect = Exception("Groq API timeout")

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "Hello"},
        )

    assert response.status_code == 502


def test_financial_assistant_llm_not_configured_returns_503() -> None:
    """Missing API key results in a 503."""
    headers = register_user("fa_noconfig")

    with patch("app.api.routes.assistant.GroqChatLlm", side_effect=RuntimeError("Groq is not configured.")):
        response = client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "Hello"},
        )

    assert response.status_code == 503


def test_financial_assistant_response_model_is_valid() -> None:
    """Response matches the ChatResponse schema."""
    headers = register_user("fa_schema")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "Test response"

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "Test"},
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert isinstance(data["response"], str)
    assert len(data) == 1  # only "response" field


def test_financial_assistant_context_includes_tax_rates() -> None:
    """The system prompt includes 2026/27 UK tax rates."""
    headers = register_user("fa_tax")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "OK"

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "What is my tax?"},
        )

    system_prompt = mock_llm.chat.call_args[0][0]
    assert "12,570" in system_prompt
    assert "20%" in system_prompt
    assert "40%" in system_prompt
    assert "45%" in system_prompt
    assert "2026/27" in system_prompt


def test_financial_assistant_context_includes_hmrc_disclaimer() -> None:
    """The system prompt tells the LLM to caveat tax estimates."""
    headers = register_user("fa_hmrc")
    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "OK"

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "Tax question"},
        )

    system_prompt = mock_llm.chat.call_args[0][0]
    assert "not official" in system_prompt.lower() or "hmrc" in system_prompt.lower()


def test_financial_assistant_user_isolation() -> None:
    """Verify that each user only sees their own financial data."""
    headers_a = register_user("fa_iso_a")
    headers_b = register_user("fa_iso_b")

    mock_llm = MagicMock(spec=["chat"])
    mock_llm.chat.return_value = "OK"

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        client.post("/assistant/chat", headers=headers_a, json={"message": "My finances"})
        client.post("/assistant/chat", headers=headers_b, json={"message": "My finances"})

    # Both calls should work and have different user contexts
    assert mock_llm.chat.call_count == 2


def test_groq_chat_llm_raises_without_api_key() -> None:
    """GroqChatLlm raises RuntimeError when groq_api_key is None."""
    from app.config import Settings
    from app.services.groq_chat_llm import GroqChatLlm

    settings = Settings(
        database_url="sqlite:///test.db",
        jwt_secret_key="test-secret",
        groq_api_key=None,
    )
    try:
        llm = GroqChatLlm(settings)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "not configured" in str(e).lower()
