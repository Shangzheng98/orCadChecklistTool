from __future__ import annotations

import os

import openai

from orcad_checker.ai.base_client import BaseLLMClient


class OpenAICompatibleClient(BaseLLMClient):
    """Client for OpenAI-compatible APIs (internal LLM deployments)."""

    def __init__(self):
        base_url = os.environ.get("OPENAI_BASE_URL", "")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not base_url:
            raise ValueError("OPENAI_BASE_URL environment variable is not set")

        self.client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed",
        )
        self.model = os.environ.get("OPENAI_MODEL", "default")

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        messages: list[dict] | None = None,
    ) -> str:
        if messages is None:
            messages = [{"role": "user", "content": user_message}]
        api_messages = [{"role": "system", "content": system_prompt}] + messages
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content
