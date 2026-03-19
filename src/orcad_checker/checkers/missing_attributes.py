from orcad_checker.checkers.base import BaseChecker
from orcad_checker.engine.registry import register_checker
from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult, Finding, Severity, Status

DEFAULT_REQUIRED = ["footprint", "value", "part_number"]


@register_checker("missing_attributes")
class MissingAttributesChecker(BaseChecker):
    name = "Missing Attributes"
    description = "Checks that components have required attributes (Footprint, Value, Part Number)"
    default_severity = "WARNING"

    def check(self, design: Design) -> list[CheckResult]:
        required = self.config.get("required_attributes", DEFAULT_REQUIRED)
        # Normalize to lowercase for matching against model fields
        required_lower = [r.lower().replace(" ", "_") for r in required]

        # Map display names
        attr_display = {
            "footprint": "Footprint",
            "value": "Value",
            "part_number": "Part Number",
        }

        findings = []
        for comp in design.components:
            missing = []
            for attr in required_lower:
                val = getattr(comp, attr, None)
                if val is None or val == "":
                    display = attr_display.get(attr, attr)
                    missing.append(display)

            if missing:
                findings.append(Finding(
                    message=f"Component '{comp.refdes}' missing: {', '.join(missing)}",
                    refdes=comp.refdes,
                    page=comp.page,
                ))

        if not findings:
            return [CheckResult(
                rule_id="missing_attributes",
                rule_name=self.name,
                severity=Severity.WARNING,
                status=Status.PASS,
            )]

        return [CheckResult(
            rule_id="missing_attributes",
            rule_name=self.name,
            severity=Severity.WARNING,
            status=Status.FAIL,
            findings=findings,
        )]
