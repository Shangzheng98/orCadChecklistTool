import re

from orcad_checker.checkers.base import BaseChecker
from orcad_checker.engine.registry import register_checker
from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult, Finding, Severity, Status

DEFAULT_FORBIDDEN = [r"^N\d{5,}$"]


@register_checker("net_naming")
class NetNamingChecker(BaseChecker):
    name = "Net Naming"
    description = "Checks for auto-generated net names that should be given meaningful names"
    default_severity = "INFO"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        forbidden = self.config.get("forbidden_patterns", DEFAULT_FORBIDDEN)
        self._patterns = [re.compile(p) for p in forbidden]

    def check(self, design: Design) -> list[CheckResult]:
        findings = []
        for net in design.nets:
            if net.is_power:
                continue
            if any(p.match(net.name) for p in self._patterns):
                findings.append(Finding(
                    message=f"Net '{net.name}' appears to be auto-generated, consider giving it a meaningful name",
                    net=net.name,
                ))

        if not findings:
            return [CheckResult(
                rule_id="net_naming",
                rule_name=self.name,
                severity=Severity.INFO,
                status=Status.PASS,
            )]

        return [CheckResult(
            rule_id="net_naming",
            rule_name=self.name,
            severity=Severity.INFO,
            status=Status.FAIL,
            findings=findings,
        )]
