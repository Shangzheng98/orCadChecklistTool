from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TemplateIssue:
    message: str
    severity: str = "error"  # error, warning


def check_template_compliance(
    code: str,
    require_checker: bool = True,
) -> list[TemplateIssue]:
    """Check if TCL code follows the checker template pattern.

    Args:
        code: TCL source code to check.
        require_checker: If True, code MUST contain a check_xxx proc.
                        If False, only validate if a check_ proc is found.
    """
    issues: list[TemplateIssue] = []

    # Look for proc check_xxx {design} pattern
    proc_match = re.search(r'proc\s+(check_\w+)\s*\{([^}]*)\}', code)

    if proc_match is None:
        if require_checker:
            issues.append(TemplateIssue(
                message="Missing 'proc check_xxx {design}' signature. Checkers must define a proc starting with 'check_'.",
                severity="error",
            ))
        return issues

    # Validate design parameter
    params = proc_match.group(2).strip()
    if "design" not in params:
        issues.append(TemplateIssue(
            message="Checker proc must accept 'design' as parameter: proc check_xxx {design}",
            severity="error",
        ))

    # Check for findings list initialization
    if "set findings" not in code:
        issues.append(TemplateIssue(
            message="Missing 'set findings [list]' initialization. Checkers should collect findings in a list.",
            severity="warning",
        ))

    # Check for check_result call
    if "check_result" not in code:
        issues.append(TemplateIssue(
            message="Missing 'check_result' call. Checkers must report results via check_result.",
            severity="error",
        ))

    return issues
