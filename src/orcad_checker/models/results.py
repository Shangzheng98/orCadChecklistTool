from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class Finding(BaseModel):
    message: str
    refdes: str = ""
    net: str = ""
    page: str = ""


class CheckResult(BaseModel):
    rule_id: str
    rule_name: str = ""
    severity: Severity = Severity.WARNING
    status: Status = Status.PASS
    findings: list[Finding] = Field(default_factory=list)


class ReportSummary(BaseModel):
    total_checks: int = 0
    passed: int = 0
    warnings: int = 0
    errors: int = 0
    infos: int = 0


class Report(BaseModel):
    result_id: str = ""
    design_name: str = ""
    timestamp: str = ""
    summary: ReportSummary = Field(default_factory=ReportSummary)
    results: list[CheckResult] = Field(default_factory=list)
    ai_summary: str = ""
