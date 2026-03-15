from orcad_checker.checkers.base import BaseChecker
from orcad_checker.engine.registry import register_checker
from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult, Finding, Severity, Status


@register_checker("single_pin_nets")
class SinglePinNetsChecker(BaseChecker):
    name = "Single Pin Nets"
    description = "Checks for nets connected to only one pin (likely a mistake)"
    default_severity = "WARNING"

    def check(self, design: Design) -> list[CheckResult]:
        ignore_power = self.config.get("ignore_power_nets", True)
        power_set = set(design.power_nets)

        findings = []
        for net in design.nets:
            if ignore_power and (net.is_power or net.name in power_set):
                continue
            if len(net.connections) == 1:
                conn = net.connections[0]
                findings.append(Finding(
                    message=f"Net '{net.name}' has only one connection: {conn.refdes} pin {conn.pin_number}",
                    net=net.name,
                    refdes=conn.refdes,
                ))

        if not findings:
            return [CheckResult(
                rule_id="single_pin_nets",
                rule_name=self.name,
                severity=Severity.WARNING,
                status=Status.PASS,
            )]

        return [CheckResult(
            rule_id="single_pin_nets",
            rule_name=self.name,
            severity=Severity.WARNING,
            status=Status.FAIL,
            findings=findings,
        )]
