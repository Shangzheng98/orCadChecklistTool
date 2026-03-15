import re

from orcad_checker.checkers.base import BaseChecker
from orcad_checker.engine.registry import register_checker
from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult, Finding, Severity, Status

DEFAULT_ALLOWED = [r"^VCC_.*", r"^VDD_.*", r"^GND.*", r"^VBAT.*", r"^VIN.*"]


@register_checker("power_net_naming")
class PowerNetNamingChecker(BaseChecker):
    name = "Power Net Naming"
    description = "Checks that power nets follow naming conventions"
    default_severity = "WARNING"

    def check(self, design: Design) -> list[CheckResult]:
        allowed = self.config.get("allowed_patterns", DEFAULT_ALLOWED)
        patterns = [re.compile(p) for p in allowed]

        findings = []
        for net in design.nets:
            if not net.is_power:
                continue
            if not any(p.match(net.name) for p in patterns):
                findings.append(Finding(
                    message=f"Power net '{net.name}' does not match naming convention",
                    net=net.name,
                ))

        if not findings:
            return [CheckResult(
                rule_id="power_net_naming",
                rule_name=self.name,
                severity=Severity.WARNING,
                status=Status.PASS,
            )]

        return [CheckResult(
            rule_id="power_net_naming",
            rule_name=self.name,
            severity=Severity.WARNING,
            status=Status.FAIL,
            findings=findings,
        )]
