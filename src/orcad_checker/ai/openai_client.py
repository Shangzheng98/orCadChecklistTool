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

    async def chat(self, system_prompt: str, user_message: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=2048,
        )
        return response.choices[0].message.content
