"""TCL check results upload endpoint — receives results from OrCAD TCL client."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
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
_recent_results: dict[str, dict] = {}
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
    _recent_results[result_id] = record
    if len(_recent_results) > MAX_HISTORY:
        oldest_key = min(_recent_results, key=lambda k: _recent_results[k]["timestamp"])
        del _recent_results[oldest_key]

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
    sorted_results = sorted(_recent_results.values(), key=lambda r: r["timestamp"], reverse=True)
    return sorted_results[:limit]


@router.get("/{result_id}")
def get_result(result_id: str):
    """Get a specific result by ID."""
    if result_id not in _recent_results:
        raise HTTPException(404, "Result not found")
    return _recent_results[result_id]
