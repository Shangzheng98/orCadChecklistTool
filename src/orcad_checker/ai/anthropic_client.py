from __future__ import annotations

import os

import anthropic

from orcad_checker.ai.base_client import BaseLLMClient


class AnthropicClient(BaseLLMClient):
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    async def chat(self, system_prompt: str, user_message: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
