from orcad_checker.checkers.base import BaseChecker
from orcad_checker.engine.registry import register_checker
from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult, Finding, Severity, Status


@register_checker("duplicate_refdes")
class DuplicateRefDesChecker(BaseChecker):
    name = "Duplicate Reference Designator"
    description = "Checks for components sharing the same RefDes"
    default_severity = "ERROR"

    def check(self, design: Design) -> list[CheckResult]:
        seen: dict[str, list[str]] = {}
        for comp in design.components:
            seen.setdefault(comp.refdes, []).append(comp.page or "unknown")

        findings = []
        for refdes, pages in seen.items():
            if len(pages) > 1:
                findings.append(Finding(
                    message=f"Duplicate RefDes '{refdes}' found on pages: {', '.join(pages)}",
                    refdes=refdes,
                ))

        if not findings:
            return [CheckResult(
                rule_id="duplicate_refdes",
                rule_name=self.name,
                severity=Severity.ERROR,
                status=Status.PASS,
            )]

        return [CheckResult(
            rule_id="duplicate_refdes",
            rule_name=self.name,
            severity=Severity.ERROR,
            status=Status.FAIL,
            findings=findings,
        )]
