from orcad_checker.checkers.base import BaseChecker
from orcad_checker.engine.registry import register_checker
from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult, Finding, Severity, Status

DEFAULT_IGNORE_NAMES = ["NC", "N/C", "DNC"]


@register_checker("unconnected_pins")
class UnconnectedPinsChecker(BaseChecker):
    name = "Unconnected Pins"
    description = "Checks for pins not connected to any net (excluding NC pins)"
    default_severity = "WARNING"

    def check(self, design: Design) -> list[CheckResult]:
        ignore_names = [
            n.upper()
            for n in self.config.get("ignore_pin_names", DEFAULT_IGNORE_NAMES)
        ]

        findings = []

        # Check explicit unconnected pins list
        for upin in design.unconnected_pins:
            if upin.pin_name.upper() not in ignore_names:
                findings.append(Finding(
                    message=f"Unconnected pin '{upin.pin_name}' (pin {upin.pin_number}) on {upin.refdes}",
                    refdes=upin.refdes,
                ))

        # Also check component pins with empty net
        for comp in design.components:
            for pin in comp.pins:
                if not pin.net and pin.name.upper() not in ignore_names:
                    findings.append(Finding(
                        message=f"Pin '{pin.name}' (pin {pin.number}) on {comp.refdes} has no net connection",
                        refdes=comp.refdes,
                        page=comp.page,
                    ))

        if not findings:
            return [CheckResult(
                rule_id="unconnected_pins",
                rule_name=self.name,
                severity=Severity.WARNING,
                status=Status.PASS,
            )]

        return [CheckResult(
            rule_id="unconnected_pins",
            rule_name=self.name,
            severity=Severity.WARNING,
            status=Status.FAIL,
            findings=findings,
        )]
