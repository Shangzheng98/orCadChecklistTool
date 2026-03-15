from __future__ import annotations

import os

from orcad_checker.ai.base_client import BaseLLMClient

SYSTEM_PROMPT = """You are an experienced electronics design review engineer.
You are reviewing OrCAD Capture schematic design check results.

Your task is to:
1. Summarize the findings in order of priority (critical errors first)
2. Explain the likely root cause of each issue
3. Provide specific, actionable recommendations to fix each issue
4. Highlight any patterns that suggest systemic design problems

Be concise but thorough. Use technical language appropriate for hardware engineers.
Respond in the same language as the input (Chinese or English)."""


def _create_client() -> BaseLLMClient:
    """Create the appropriate LLM client based on configuration."""
    provider = os.environ.get("AI_PROVIDER", "anthropic").lower()

    if provider == "openai_compatible":
        from orcad_checker.ai.openai_client import OpenAICompatibleClient
        return OpenAICompatibleClient()
    else:
        from orcad_checker.ai.anthropic_client import AnthropicClient
        return AnthropicClient()


async def generate_summary(report_json: str) -> str:
    """Generate an AI summary for the given check report JSON."""
    client = _create_client()

    user_message = f"""Please analyze and summarize the following OrCAD schematic check results:

{report_json}"""

    return await client.chat(SYSTEM_PROMPT, user_message)
