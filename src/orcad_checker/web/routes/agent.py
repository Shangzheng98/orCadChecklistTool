"""AI Agent API — conversational TCL script generation."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from orcad_checker.ai.tcl_agent import chat_with_agent, extract_tcl_code
from orcad_checker.models.scripts import AgentMessage, ScriptCategory, ScriptMeta
from orcad_checker.store.database import Database
from orcad_checker.web.deps import get_db

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

logger = logging.getLogger(__name__)

MAX_SESSIONS = 200
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
async def agent_chat(req: ChatRequest, db: Database = Depends(get_db)):
    session_id = req.session_id or str(uuid.uuid4())[:8]

    # Get or create session with eviction
    if session_id not in _sessions:
        if len(_sessions) >= MAX_SESSIONS:
            oldest_key = next(iter(_sessions))
            del _sessions[oldest_key]
        _sessions[session_id] = []

    messages = _sessions[session_id]
    messages.append(AgentMessage(role="user", content=req.message))

    try:
        reply = await chat_with_agent(messages, db=db)
    except ValueError as e:
        logger.warning("Invalid input for session %s: %s", session_id, e)
        raise HTTPException(400, str(e))
    except TimeoutError as e:
        logger.error("AI timeout for session %s: %s", session_id, e)
        raise HTTPException(504, "AI service timeout")
    except Exception as e:
        logger.exception("Unexpected error in agent_chat for session %s", session_id)
        raise HTTPException(500, "Internal server error")

    messages.append(AgentMessage(role="assistant", content=reply))

    code = extract_tcl_code(reply)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        extracted_code=code,
    )


@router.post("/save")
def save_generated_script(req: SaveScriptRequest, db: Database = Depends(get_db)):
    """Save the generated script from an agent session to the script repository."""
    code = req.code
    if not code and req.session_id in _sessions:
        for msg in reversed(_sessions[req.session_id]):
            if msg.role == "assistant":
                code = extract_tcl_code(msg.content)
                if code:
                    break

    if not code:
        raise HTTPException(400, "No TCL code found to save")

    meta = ScriptMeta(
        name=req.name, description=req.description,
        category=req.category, author=req.author, tags=req.tags,
    )
    result = db.create_script(meta, code)
    return result


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    messages = _sessions.get(session_id, [])
    return {"session_id": session_id, "messages": messages}


@router.delete("/sessions/{session_id}")
def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"status": "cleared"}
