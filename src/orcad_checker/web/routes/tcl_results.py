"""TCL check results upload endpoint — receives results from OrCAD TCL client."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/check-results", tags=["tcl-results"])


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


# In-memory store for recent uploads (production: use DB)
_recent_results: list[dict] = []
MAX_HISTORY = 100


@router.post("/upload", response_model=UploadResponse)
def upload_tcl_results(data: TclResultUpload):
    """Receive check results from the OrCAD TCL client."""
    result_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()

    errors = sum(1 for r in data.results if r.status == "FAIL" and r.severity == "ERROR")
    warnings = sum(1 for r in data.results if r.status == "FAIL" and r.severity == "WARNING")

    record = {
        "result_id": result_id,
        "design_name": data.design_name,
        "source": data.source,
        "timestamp": timestamp,
        "results": [r.model_dump() for r in data.results],
    }
    _recent_results.append(record)
    if len(_recent_results) > MAX_HISTORY:
        _recent_results.pop(0)

    return UploadResponse(
        result_id=result_id,
        design_name=data.design_name,
        timestamp=timestamp,
        total_checks=len(data.results),
        errors=errors,
        warnings=warnings,
    )


@router.get("/history")
def get_result_history(limit: int = 20):
    """Get recent TCL check result uploads."""
    return _recent_results[-limit:]


@router.get("/{result_id}")
def get_result(result_id: str):
    """Get a specific result by ID."""
    for r in _recent_results:
        if r["result_id"] == result_id:
            return r
    return {"error": "Not found"}
