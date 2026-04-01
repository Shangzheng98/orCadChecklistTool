from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from orcad_checker.engine.registry import discover_checkers, list_checkers
from orcad_checker.engine.runner import run_checks
from orcad_checker.models.results import Report
from orcad_checker.parser.design_parser import parse_design_dict

router = APIRouter(prefix="/api/v1", tags=["checks"])


class CheckerInfo(BaseModel):
    id: str
    name: str
    description: str
    default_severity: str


@router.get("/checkers", response_model=list[CheckerInfo])
def get_checkers():
    """List all available checkers."""
    discover_checkers()
    checkers = list_checkers()
    return [
        CheckerInfo(
            id=rule_id,
            name=cls.name,
            description=cls.description,
            default_severity=cls.default_severity,
        )
        for rule_id, cls in sorted(checkers.items())
    ]


@router.post("/check", response_model=Report)
async def run_check(
    file: UploadFile = File(...),
    selected_checkers: str = Form(default=""),
):
    """Upload a design JSON and run selected checkers."""
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File too large (max 50MB)")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON format")
    try:
        design = parse_design_dict(data)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, f"Invalid design format: {str(e)[:200]}")

    selected = (
        [s.strip() for s in selected_checkers.split(",") if s.strip()]
        if selected_checkers
        else None
    )

    report = run_checks(design, selected_checkers=selected)
    return report
