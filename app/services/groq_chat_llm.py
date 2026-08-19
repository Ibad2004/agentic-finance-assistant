"""Groq adapter for the provider-neutral ChatLlm interface."""

from __future__ import annotations

import logging

from langchain_groq import ChatGroq

from app.config import Settings

logger = logging.getLogger(__name__)


class GroqChatLlm:
    """Calls Groq for general-purpose conversational responses."""

    def __init__(self, settings: Settings) -> None:
        if settings.groq_api_key is None:
            raise RuntimeError("Groq is not configured.")
        self._model = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key.get_secret_value(),
            temperature=0.3,
            max_tokens=1024,
        )

    def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a message with system context and return the response."""
        messages = [
            ("system", system_prompt),
            ("human", user_message),
        ]
        result = self._model.invoke(messages)
        return result.content
