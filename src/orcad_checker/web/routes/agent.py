"""AI Agent API — conversational TCL script generation."""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from orcad_checker.ai.tcl_agent import chat_with_agent, extract_tcl_code
from orcad_checker.models.scripts import AgentMessage, ScriptCategory, ScriptMeta
from orcad_checker.store.database import Database

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

_db = Database()

# In-memory session store (for simplicity; could be Redis/DB for production)
_sessions: dict[str, list[AgentMessage]] = {}


class ChatRequest(BaseModel):
    session_id: str = ""
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    extracted_code: str = ""


class SaveScriptRequest(BaseModel):
    session_id: str
    name: str
    description: str = ""
    category: ScriptCategory = ScriptCategory.CUSTOM
    author: str = ""
    tags: list[str] = []
    code: str = ""  # If empty, extract from last agent response


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())[:8]

    # Get or create session
    if session_id not in _sessions:
        _sessions[session_id] = []

    messages = _sessions[session_id]
    messages.append(AgentMessage(role="user", content=req.message))

    try:
        reply = await chat_with_agent(messages, db=_db)
    except Exception as e:
        return ChatResponse(
            session_id=session_id,
            reply=f"Error: {e}",
        )

    messages.append(AgentMessage(role="assistant", content=reply))

    code = extract_tcl_code(reply)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        extracted_code=code,
    )


@router.post("/save")
def save_generated_script(req: SaveScriptRequest):
    """Save the generated script from an agent session to the script repository."""
    code = req.code
    if not code and req.session_id in _sessions:
        # Extract code from the last assistant message
        for msg in reversed(_sessions[req.session_id]):
            if msg.role == "assistant":
                code = extract_tcl_code(msg.content)
                if code:
                    break

    if not code:
        return {"error": "No TCL code found to save"}

    meta = ScriptMeta(
        name=req.name, description=req.description,
        category=req.category, author=req.author, tags=req.tags,
    )
    result = _db.create_script(meta, code)
    return result


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    messages = _sessions.get(session_id, [])
    return {"session_id": session_id, "messages": messages}


@router.delete("/sessions/{session_id}")
def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"status": "cleared"}
