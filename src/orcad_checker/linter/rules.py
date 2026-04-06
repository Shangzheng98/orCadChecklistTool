from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SafetyRule:
    pattern: str
    severity: str      # fatal, error, warning
    message: str
    category: str      # crash_zone, syntax, convention
    fix: str = ""
    is_regex: bool = False


def load_safety_rules(rules_path: Path) -> list[SafetyRule]:
    """Load safety rules from YAML file."""
    if not rules_path.exists():
        raise FileNotFoundError(f"Safety rules file not found: {rules_path}")

    with open(rules_path) as f:
        data = yaml.safe_load(f)

    rules: list[SafetyRule] = []

    for entry in data.get("crash_zones", []):
        rules.append(SafetyRule(
            pattern=entry["pattern"],
            severity=entry.get("severity", "fatal"),
            message=entry["message"],
            category="crash_zone",
            fix=entry.get("fix", ""),
            is_regex=entry.get("is_regex", False),
        ))

    for entry in data.get("syntax_hazards", []):
        rules.append(SafetyRule(
            pattern=entry["pattern"],
            severity=entry.get("severity", "warning"),
            message=entry["message"],
            category="syntax",
            fix=entry.get("fix", ""),
            is_regex=entry.get("is_regex", True),
        ))

    for entry in data.get("conventions", []):
        rules.append(SafetyRule(
            pattern=entry["pattern"],
            severity=entry.get("severity", "warning"),
            message=entry["message"],
            category="convention",
            fix=entry.get("fix", ""),
            is_regex=entry.get("is_regex", False),
        ))

    return rules
