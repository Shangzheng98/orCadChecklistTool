from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

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
async def get_checkers():
    """List all available checkers."""
    await run_in_threadpool(discover_checkers)
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
    content = await file.read()
    data = json.loads(content)
    design = parse_design_dict(data)

    selected = (
        [s.strip() for s in selected_checkers.split(",") if s.strip()]
        if selected_checkers
        else None
    )

    report = await run_in_threadpool(lambda: run_checks(design, selected_checkers=selected))
    return report
