from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a message and return the response text."""
        ...
