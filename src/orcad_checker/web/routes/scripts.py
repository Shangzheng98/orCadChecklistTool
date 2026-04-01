"""Script repository API — CRUD, versioning, publishing, OTA."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from orcad_checker.models.scripts import ScriptCategory, ScriptMeta, ScriptStatus
from orcad_checker.store.database import Database
from orcad_checker.web.deps import get_db

router = APIRouter(prefix="/api/v1/scripts", tags=["scripts"])


class CreateScriptRequest(BaseModel):
    name: str
    description: str = ""
    category: ScriptCategory = ScriptCategory.CUSTOM
    author: str = ""
    tags: list[str] = []
    code: str


class UpdateScriptRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: ScriptCategory | None = None
    tags: list[str] | None = None
    code: str | None = None
    changelog: str = ""


# ── List / Search ────────────────────────────────────────────

@router.get("")
async def list_scripts(
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    db: Database = Depends(get_db),
):
    return await run_in_threadpool(db.list_scripts, status, category, search)


# ── CRUD ─────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_script(req: CreateScriptRequest, db: Database = Depends(get_db)):
    meta = ScriptMeta(
        name=req.name, description=req.description,
        category=req.category, author=req.author, tags=req.tags,
    )
    return await run_in_threadpool(db.create_script, meta, req.code)


@router.get("/{script_id}")
async def get_script(script_id: str, db: Database = Depends(get_db)):
    script = await run_in_threadpool(db.get_script, script_id)
    if not script:
        raise HTTPException(404, "Script not found")
    return script


@router.put("/{script_id}")
async def update_script(script_id: str, req: UpdateScriptRequest, db: Database = Depends(get_db)):
    meta = None
    if any([req.name, req.description, req.category, req.tags]):
        meta = ScriptMeta(
            name=req.name or "",
            description=req.description or "",
            category=req.category or ScriptCategory.CUSTOM,
            tags=req.tags or [],
        )
    result = await run_in_threadpool(db.update_script, script_id, meta, req.code, req.changelog)
    if not result:
        raise HTTPException(404, "Script not found")
    return result


@router.delete("/{script_id}")
async def delete_script(script_id: str, db: Database = Depends(get_db)):
    deleted = await run_in_threadpool(db.delete_script, script_id)
    if not deleted:
        raise HTTPException(404, "Script not found")
    return {"status": "deleted"}


# ── Versioning ───────────────────────────────────────────────

@router.get("/{script_id}/versions")
async def get_versions(script_id: str, db: Database = Depends(get_db)):
    versions = await run_in_threadpool(db.get_script_versions, script_id)
    if not versions:
        raise HTTPException(404, "Script not found or no versions")
    return versions


# ── Publishing ───────────────────────────────────────────────

@router.post("/{script_id}/publish")
async def publish_script(script_id: str, db: Database = Depends(get_db)):
    result = await run_in_threadpool(db.publish_script, script_id)
    if not result:
        raise HTTPException(404, "Script not found")
    return result


# ── OTA ──────────────────────────────────────────────────────

@router.get("/ota/manifest")
async def ota_manifest(client_id: str | None = None, db: Database = Depends(get_db)):
    return await run_in_threadpool(db.build_ota_manifest, client_id)


@router.get("/ota/download/{script_id}")
async def ota_download(script_id: str, db: Database = Depends(get_db)):
    """Download a specific script for OTA install."""
    script = await run_in_threadpool(db.get_script, script_id)
    if not script:
        raise HTTPException(404, "Script not found")
    return script
