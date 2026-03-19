from orcad_checker.checkers.base import BaseChecker
from orcad_checker.engine.registry import register_checker
from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult, Finding, Severity, Status


@register_checker("footprint_validation")
class FootprintValidationChecker(BaseChecker):
    name = "Footprint Validation"
    description = "Checks that all components have a footprint assigned"
    default_severity = "ERROR"

    def check(self, design: Design) -> list[CheckResult]:
        findings = []
        for comp in design.components:
            if not comp.footprint:
                findings.append(Finding(
                    message=f"Component '{comp.refdes}' ({comp.part_name}) has no footprint assigned",
                    refdes=comp.refdes,
                    page=comp.page,
                ))

        if not findings:
            return [CheckResult(
                rule_id="footprint_validation",
                rule_name=self.name,
                severity=Severity.ERROR,
                status=Status.PASS,
            )]

        return [CheckResult(
            rule_id="footprint_validation",
            rule_name=self.name,
            severity=Severity.ERROR,
            status=Status.FAIL,
            findings=findings,
        )]
