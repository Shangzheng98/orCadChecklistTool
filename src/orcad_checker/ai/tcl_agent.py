"""AI Agent that generates TCL scripts from natural language using knowledge base context."""
from __future__ import annotations

import os

from orcad_checker.ai.base_client import BaseLLMClient
from orcad_checker.models.scripts import AgentMessage, KnowledgeDoc
from orcad_checker.store.database import Database

SYSTEM_PROMPT = """You are an expert OrCAD Capture TCL scripting assistant.

You help hardware engineers create TCL scripts for OrCAD Capture by:
1. Understanding what they want to accomplish in natural language
2. Generating correct, production-ready TCL code using OrCAD Capture's TCL API
3. Explaining each section of the generated code
4. Following best practices for OrCAD TCL scripting

## Key Rules:
- Use only documented OrCAD Capture TCL commands
- Include proper error handling (catch blocks)
- Add comments in both English and Chinese where helpful
- Always verify design is open before operations
- Clean up resources (close files, release objects)
- Use consistent variable naming (camelCase for local, UPPER_CASE for constants)

## Reference Knowledge:
{knowledge_context}

Respond in the same language as the user's input (Chinese or English).
When generating code, wrap it in ```tcl ... ``` blocks."""


def _create_client() -> BaseLLMClient:
    provider = os.environ.get("AI_PROVIDER", "anthropic").lower()
    if provider == "openai_compatible":
        from orcad_checker.ai.openai_client import OpenAICompatibleClient
        return OpenAICompatibleClient()
    else:
        from orcad_checker.ai.anthropic_client import AnthropicClient
        return AnthropicClient()


def _build_knowledge_context(db: Database, user_message: str) -> str:
    """Search knowledge base for relevant docs to include as context."""
    # Extract key terms from user message for search
    docs = db.search_knowledge(user_message, limit=5)
    if not docs:
        return "(No specific API documentation found. Use general OrCAD TCL knowledge.)"

    parts = []
    for doc in docs:
        parts.append(f"### {doc.title} [{doc.category}]\n{doc.content}\n")
    return "\n".join(parts)


async def chat_with_agent(
    messages: list[AgentMessage],
    db: Database | None = None,
) -> str:
    """Multi-turn conversation with TCL generation agent.

    Args:
        messages: Conversation history (user + assistant turns).
        db: Database instance for knowledge base lookup.
    """
    if not db:
        db = Database()

    client = _create_client()

    # Get the latest user message for knowledge search
    latest_user_msg = ""
    for msg in reversed(messages):
        if msg.role == "user":
            latest_user_msg = msg.content
            break

    knowledge_context = _build_knowledge_context(db, latest_user_msg)
    system = SYSTEM_PROMPT.format(knowledge_context=knowledge_context)

    # Build conversation as a single user message (for compatibility with both providers)
    conversation_parts = []
    for msg in messages:
        prefix = "User" if msg.role == "user" else "Assistant"
        conversation_parts.append(f"{prefix}: {msg.content}")

    full_message = "\n\n".join(conversation_parts)

    return await client.chat(system, full_message)


def extract_tcl_code(response: str) -> str:
    """Extract TCL code blocks from agent response."""
    blocks = []
    in_block = False
    current: list[str] = []

    for line in response.split("\n"):
        if line.strip().startswith("```tcl"):
            in_block = True
            current = []
        elif line.strip() == "```" and in_block:
            in_block = False
            blocks.append("\n".join(current))
        elif in_block:
            current.append(line)

    return "\n\n".join(blocks) if blocks else ""
