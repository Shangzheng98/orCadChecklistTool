"""AI Agent API — conversational TCL script generation."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

from orcad_checker.ai.tcl_agent import chat_with_agent
from orcad_checker.models.scripts import AgentMessage, ScriptCategory, ScriptMeta
from orcad_checker.store.database import Database
from orcad_checker.web.deps import get_db

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

MAX_SESSIONS = 200

# In-memory clipboard for passing code from browser to OrCAD
_tcl_clipboard: dict = {"code": "", "description": ""}


class ClipboardRequest(BaseModel):
    code: str
    description: str = ""


@router.post("/clipboard")
async def set_clipboard(req: ClipboardRequest):
    """Browser sends generated TCL code here."""
    _tcl_clipboard["code"] = req.code
    _tcl_clipboard["description"] = req.description
    return {"status": "ok"}


@router.get("/clipboard")
async def get_clipboard():
    """OrCAD fetches the code from here."""
    return _tcl_clipboard


@router.delete("/clipboard")
async def clear_clipboard():
    _tcl_clipboard["code"] = ""
    _tcl_clipboard["description"] = ""
    return {"status": "cleared"}


class ChatRequest(BaseModel):
    session_id: str = ""
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    extracted_code: str = ""
    lint_passed: bool | None = None
    lint_summary: str = ""
    lint_issues: list[dict] = []


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

    # Get or create session from DB
    raw_messages = await run_in_threadpool(db.get_session, session_id)
    if raw_messages is None:
        # Evict oldest if at capacity
        count = await run_in_threadpool(db.count_sessions)
        if count >= MAX_SESSIONS:
            await run_in_threadpool(db.delete_oldest_session)
        raw_messages = []

    messages = [AgentMessage(**m) for m in raw_messages]
    messages.append(AgentMessage(role="user", content=req.message))

    try:
        reply = await chat_with_agent(messages, db=db)
    except Exception as e:
        logger.exception("Agent chat failed for session %s", session_id)
        raise HTTPException(status_code=502, detail=f"AI service error: {e}")

    messages.append(AgentMessage(role="assistant", content=reply))

    # Persist session
    await run_in_threadpool(
        db.save_session, session_id, [m.model_dump() for m in messages]
    )

    from orcad_checker.ai.tcl_agent import extract_and_lint_tcl
    code, lint_report = extract_and_lint_tcl(reply)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        extracted_code=code,
        lint_passed=lint_report.passed if lint_report else None,
        lint_summary=lint_report.summary if lint_report else "",
        lint_issues=[i.to_dict() for i in (lint_report.issues if lint_report else [])],
    )


@router.post("/save")
async def save_generated_script(req: SaveScriptRequest, db: Database = Depends(get_db)):
    """Save the generated script from an agent session to the script repository."""
    from orcad_checker.ai.tcl_agent import extract_tcl_code as _extract_tcl_code
    code = req.code
    if not code:
        raw_messages = await run_in_threadpool(db.get_session, req.session_id)
        if raw_messages:
            for msg_data in reversed(raw_messages):
                if msg_data.get("role") == "assistant":
                    code = _extract_tcl_code(msg_data.get("content", ""))
                    if code:
                        break

    if not code:
        return {"error": "No TCL code found to save"}

    meta = ScriptMeta(
        name=req.name, description=req.description,
        category=req.category, author=req.author, tags=req.tags,
    )
    result = await run_in_threadpool(db.create_script, meta, code)
    return result


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: Database = Depends(get_db)):
    raw_messages = await run_in_threadpool(db.get_session, session_id)
    messages = raw_messages if raw_messages is not None else []
    return {"session_id": session_id, "messages": messages}


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str, db: Database = Depends(get_db)):
    # Delete by saving empty or just let it be — simplest: delete via direct SQL
    # For now, save an empty list to effectively clear
    await run_in_threadpool(db.save_session, session_id, [])
    return {"status": "cleared"}
