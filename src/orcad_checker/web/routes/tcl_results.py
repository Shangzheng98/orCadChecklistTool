"""TCL check results upload endpoint — receives results from OrCAD TCL client."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from orcad_checker.store.database import Database
from orcad_checker.web.deps import get_db

router = APIRouter(prefix="/api/v1/check-results", tags=["tcl-results"])

MAX_HISTORY = 100


class TclFinding(BaseModel):
    message: str
    refdes: str = ""
    net: str = ""
    page: str = ""


class TclCheckResult(BaseModel):
    rule_id: str
    severity: str = "WARNING"
    status: str = "PASS"
    findings: list[TclFinding] = Field(default_factory=list)


class TclResultUpload(BaseModel):
    design_name: str
    source: str = "orcad_tcl"
    results: list[TclCheckResult] = Field(default_factory=list)


class UploadResponse(BaseModel):
    result_id: str
    design_name: str
    timestamp: str
    total_checks: int
    errors: int
    warnings: int


@router.post("/upload", response_model=UploadResponse)
async def upload_tcl_results(data: TclResultUpload, db: Database = Depends(get_db)):
    """Receive check results from the OrCAD TCL client."""
    result_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()

    errors = sum(1 for r in data.results if r.status == "FAIL" and r.severity == "ERROR")
    warnings = sum(1 for r in data.results if r.status == "FAIL" and r.severity == "WARNING")

    results_data = [r.model_dump() for r in data.results]

    await run_in_threadpool(
        db.save_tcl_result, result_id, data.design_name, data.source, timestamp, results_data
    )

    # Evict oldest if over capacity
    result_count = len(await run_in_threadpool(db.list_tcl_results, MAX_HISTORY + 1))
    if result_count > MAX_HISTORY:
        await run_in_threadpool(db.evict_oldest_tcl_result)

    return UploadResponse(
        result_id=result_id,
        design_name=data.design_name,
        timestamp=timestamp,
        total_checks=len(data.results),
        errors=errors,
        warnings=warnings,
    )


@router.get("/history")
async def get_result_history(limit: int = 20, db: Database = Depends(get_db)):
    """Get recent TCL check result uploads."""
    return await run_in_threadpool(db.list_tcl_results, limit)


@router.get("/{result_id}")
async def get_result(result_id: str, db: Database = Depends(get_db)):
    """Get a specific result by ID."""
    result = await run_in_threadpool(db.get_tcl_result, result_id)
    if not result:
        return {"error": "Not found"}
    return result
