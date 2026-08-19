"""Tests for the AI Financial Assistant endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.groq_chat_llm import GroqChatLlm

client = TestClient(app)


def register_user(prefix: str = "assistant_user") -> dict[str, str]:
    """Register a user and return auth headers."""
    email = f"{prefix}_{uuid4().hex[:8]}@example.com"
    password = "AssistantTest123!"
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_chat_requires_authentication_returns_401() -> None:
    response = client.post(
        "/assistant/chat",
        json={"message": "Hello"},
    )
    assert response.status_code == 401


def test_chat_empty_message_returns_422() -> None:
    headers = register_user()
    response = client.post(
        "/assistant/chat",
        headers=headers,
        json={"message": ""},
    )
    assert response.status_code == 422


def test_chat_missing_message_returns_422() -> None:
    headers = register_user()
    response = client.post(
        "/assistant/chat",
        headers=headers,
        json={},
    )
    assert response.status_code == 422


def test_chat_message_too_long_returns_422() -> None:
    headers = register_user()
    response = client.post(
        "/assistant/chat",
        headers=headers,
        json={"message": "x" * 2001},
    )
    assert response.status_code == 422


def test_chat_no_transactions_returns_context_and_llm_response() -> None:
    """Chat works even when the user has no transactions — context just says 0."""
    headers = register_user("empty_user")

    mock_llm = MagicMock(spec=GroqChatLlm)
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

    system_prompt = mock_llm.chat.call_args[0][0]
    assert "Total transactions: 0" in system_prompt
    assert "Total income:" in system_prompt
    assert "Total expenses:" in system_prompt


def test_chat_includes_user_financial_context_in_system_prompt() -> None:
    """The system prompt includes user financial context."""
    headers = register_user("context_user")

    mock_llm = MagicMock(spec=GroqChatLlm)
    mock_llm.chat.return_value = "Based on your data..."

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "What do I spend the most on?"},
        )

    assert response.status_code == 200
    system_prompt = mock_llm.chat.call_args[0][0]
    assert "User:" in system_prompt
    assert "Total transactions:" in system_prompt
    assert "Total income:" in system_prompt
    assert "Total expenses:" in system_prompt
    assert "Net:" in system_prompt


def test_chat_passes_user_message_to_llm() -> None:
    """The user's message is passed as the second argument to llm.chat()."""
    headers = register_user("msg_user")

    mock_llm = MagicMock(spec=GroqChatLlm)
    mock_llm.chat.return_value = "Based on your data..."

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "How much did I spend on food?"},
        )

    user_message = mock_llm.chat.call_args[0][1]
    assert user_message == "How much did I spend on food?"


def test_chat_returns_502_when_llm_call_fails() -> None:
    """LLM failure results in a 502 error, not an unhandled exception."""
    headers = register_user("fail_user")

    mock_llm = MagicMock(spec=GroqChatLlm)
    mock_llm.chat.side_effect = Exception("Groq API timeout")

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        response = client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "Hello"},
        )

    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"].lower()


def test_chat_returns_503_when_llm_not_configured() -> None:
    """Missing API key results in a 503."""
    headers = register_user("noconfig_user")

    with patch("app.api.routes.assistant.GroqChatLlm", side_effect=RuntimeError("Groq is not configured.")):
        response = client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "Hello"},
        )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_chat_response_model_is_valid() -> None:
    """Response matches the ChatResponse schema."""
    headers = register_user("schema_user")

    mock_llm = MagicMock(spec=GroqChatLlm)
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


def test_chat_system_prompt_contains_tax_rates() -> None:
    """The system prompt includes 2026/27 UK tax rates."""
    headers = register_user("tax_prompt_user")

    mock_llm = MagicMock(spec=GroqChatLlm)
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


def test_chat_system_prompt_reminds_not_official_hmrc() -> None:
    """The system prompt tells the LLM to caveat tax estimates."""
    headers = register_user("hmrc_user")

    mock_llm = MagicMock(spec=GroqChatLlm)
    mock_llm.chat.return_value = "OK"

    with patch("app.api.routes.assistant.GroqChatLlm", return_value=mock_llm):
        client.post(
            "/assistant/chat",
            headers=headers,
            json={"message": "Tax question"},
        )

    system_prompt = mock_llm.chat.call_args[0][0]
    assert "not official" in system_prompt.lower() or "hmrc" in system_prompt.lower()


def test_groq_chat_llm_raises_without_api_key() -> None:
    """GroqChatLlm raises RuntimeError when groq_api_key is None."""
    from app.config import Settings

    settings = Settings(
        database_url="sqlite:///test.db",
        jwt_secret_key="test-secret",
        groq_api_key=None,
    )
    try:
        llm = GroqChatLlm(settings)
        # Should not reach here
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "not configured" in str(e).lower()
