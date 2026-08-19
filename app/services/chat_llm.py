"""Provider-neutral interface for conversational LLMs."""

from typing import Protocol


class ChatLlm(Protocol):
    """Protocol for general-purpose conversational LLM providers."""

    def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a message with system context and return the assistant response.

        Args:
            system_prompt: The system-level instructions and context.
            user_message: The user's message.

        Returns:
            The LLM's response text.

        Raises:
            RuntimeError: If the LLM provider is unavailable or the call fails.
        """
        ...
