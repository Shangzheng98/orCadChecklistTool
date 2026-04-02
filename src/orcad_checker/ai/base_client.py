from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        messages: list[dict] | None = None,
    ) -> str:
        """Send a message and return the response text.

        Args:
            system_prompt: System prompt for the model.
            user_message: Single user message (used when messages is None).
            messages: Full conversation history as list of {"role", "content"} dicts.
                      When provided, user_message is ignored.
        """
        ...
