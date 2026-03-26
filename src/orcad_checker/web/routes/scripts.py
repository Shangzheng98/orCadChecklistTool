"""Script repository API — CRUD, versioning, publishing, OTA."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from orcad_checker.models.scripts import ScriptCategory, ScriptMeta, ScriptStatus
from orcad_checker.store.database import Database

router = APIRouter(prefix="/api/v1/scripts", tags=["scripts"])

_db = Database()


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
def list_scripts(
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
):
    return _db.list_scripts(status=status, category=category, search=search)


# ── CRUD ─────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_script(req: CreateScriptRequest):
    meta = ScriptMeta(
        name=req.name, description=req.description,
        category=req.category, author=req.author, tags=req.tags,
    )
    return _db.create_script(meta, req.code)


@router.get("/{script_id}")
def get_script(script_id: str):
    script = _db.get_script(script_id)
    if not script:
        raise HTTPException(404, "Script not found")
    return script


@router.put("/{script_id}")
def update_script(script_id: str, req: UpdateScriptRequest):
    meta = None
    if any([req.name, req.description, req.category, req.tags]):
        meta = ScriptMeta(
            name=req.name or "",
            description=req.description or "",
            category=req.category or ScriptCategory.CUSTOM,
            tags=req.tags or [],
        )
    result = _db.update_script(script_id, meta=meta, code=req.code, changelog=req.changelog)
    if not result:
        raise HTTPException(404, "Script not found")
    return result


@router.delete("/{script_id}")
def delete_script(script_id: str):
    if not _db.delete_script(script_id):
        raise HTTPException(404, "Script not found")
    return {"status": "deleted"}


# ── Versioning ───────────────────────────────────────────────

@router.get("/{script_id}/versions")
def get_versions(script_id: str):
    versions = _db.get_script_versions(script_id)
    if not versions:
        raise HTTPException(404, "Script not found or no versions")
    return versions


# ── Publishing ───────────────────────────────────────────────

@router.post("/{script_id}/publish")
def publish_script(script_id: str):
    result = _db.publish_script(script_id)
    if not result:
        raise HTTPException(404, "Script not found")
    return result


# ── OTA ──────────────────────────────────────────────────────

@router.get("/ota/manifest")
def ota_manifest(client_id: str | None = None):
    return _db.build_ota_manifest(client_id)


@router.get("/ota/download/{script_id}")
def ota_download(script_id: str):
    """Download a specific script for OTA install."""
    script = _db.get_script(script_id)
    if not script:
        raise HTTPException(404, "Script not found")
    return script
