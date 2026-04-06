from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from orcad_checker.linter.rules import SafetyRule, load_safety_rules

_DEFAULT_RULES_PATH = Path(__file__).parent.parent.parent.parent / "rules" / "tcl_safety_rules.yaml"


@dataclass
class LintIssue:
    severity: str       # fatal, error, warning
    category: str       # crash_zone, syntax, convention
    message: str
    line: int = 0
    matched_text: str = ""
    fix: str = ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "line": self.line,
            "matched_text": self.matched_text,
            "fix": self.fix,
        }


def scan_tcl_code(
    code: str,
    rules: list[SafetyRule] | None = None,
) -> list[LintIssue]:
    """Scan TCL code against safety rules and return issues found."""
    if rules is None:
        rules = load_safety_rules(_DEFAULT_RULES_PATH)

    issues: list[LintIssue] = []
    lines = code.split("\n")

    for rule in rules:
        if rule.is_regex:
            try:
                pattern = re.compile(rule.pattern)
            except re.error:
                continue
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    issues.append(LintIssue(
                        severity=rule.severity,
                        category=rule.category,
                        message=rule.message,
                        line=i,
                        matched_text=line.strip(),
                        fix=rule.fix,
                    ))
        else:
            for i, line in enumerate(lines, 1):
                if rule.pattern in line:
                    issues.append(LintIssue(
                        severity=rule.severity,
                        category=rule.category,
                        message=rule.message,
                        line=i,
                        matched_text=line.strip(),
                        fix=rule.fix,
                    ))

    # Sort by severity (fatal first), then line number
    severity_order = {"fatal": 0, "error": 1, "warning": 2}
    issues.sort(key=lambda i: (severity_order.get(i.severity, 9), i.line))

    return issues
