from __future__ import annotations

from fastapi import APIRouter, Body
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["summary"])


class SummaryRequest(BaseModel):
    report_json: str


class SummaryResponse(BaseModel):
    summary: str
    error: str = ""


@router.post("/summarize", response_model=SummaryResponse)
async def summarize(request: SummaryRequest):
    """Generate AI summary for check results."""
    try:
        from orcad_checker.ai.summarizer import generate_summary
        summary = await generate_summary(request.report_json)
        return SummaryResponse(summary=summary)
    except Exception as e:
        return SummaryResponse(summary="", error=str(e))
