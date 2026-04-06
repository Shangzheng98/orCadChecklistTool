from __future__ import annotations

from dataclasses import dataclass, field

from orcad_checker.linter.scanner import LintIssue, scan_tcl_code
from orcad_checker.linter.template_checker import check_template_compliance


@dataclass
class LintReport:
    passed: bool
    issues: list[LintIssue] = field(default_factory=list)
    template_issues: list = field(default_factory=list)
    fatal_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "fatal_count": self.fatal_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "summary": self.summary,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "line": i.line,
                    "matched_text": i.matched_text,
                    "fix": i.fix,
                }
                for i in self.issues
            ],
            "template_issues": [
                {"message": t.message, "severity": t.severity}
                for t in self.template_issues
            ],
        }


def lint_tcl(
    code: str,
    require_checker: bool = True,
) -> LintReport:
    """Run all lint checks on TCL code and return a report.

    Args:
        code: TCL source code.
        require_checker: Whether to require checker template compliance.

    Returns:
        LintReport with pass/fail status, issues, and summary.
    """
    # Run safety scanner
    scan_issues = scan_tcl_code(code)

    # Run template compliance
    template_issues = check_template_compliance(code, require_checker=require_checker)

    # Count by severity
    fatal_count = sum(1 for i in scan_issues if i.severity == "fatal")
    error_count = (
        sum(1 for i in scan_issues if i.severity == "error")
        + sum(1 for t in template_issues if t.severity == "error")
    )
    warning_count = (
        sum(1 for i in scan_issues if i.severity == "warning")
        + sum(1 for t in template_issues if t.severity == "warning")
    )

    # Lint fails if any fatal or error issues
    passed = fatal_count == 0 and error_count == 0

    # Build summary
    parts = []
    if fatal_count:
        parts.append(f"{fatal_count} fatal (crash zone)")
    if error_count:
        parts.append(f"{error_count} error")
    if warning_count:
        parts.append(f"{warning_count} warning")
    if passed and not parts:
        summary = "All checks passed."
    elif passed:
        summary = f"Passed with warnings: {', '.join(parts)}."
    else:
        summary = f"BLOCKED: {', '.join(parts)}."

    return LintReport(
        passed=passed,
        issues=scan_issues,
        template_issues=template_issues,
        fatal_count=fatal_count,
        error_count=error_count,
        warning_count=warning_count,
        summary=summary,
    )
