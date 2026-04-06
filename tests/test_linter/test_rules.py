from pathlib import Path

from orcad_checker.linter.rules import load_safety_rules, SafetyRule

RULES_PATH = Path(__file__).parent.parent.parent / "rules" / "tcl_safety_rules.yaml"


def test_load_safety_rules_returns_list():
    rules = load_safety_rules(RULES_PATH)
    assert isinstance(rules, list)
    assert len(rules) > 0


def test_each_rule_has_required_fields():
    rules = load_safety_rules(RULES_PATH)
    for rule in rules:
        assert isinstance(rule, SafetyRule)
        assert rule.pattern != ""
        assert rule.severity in ("fatal", "error", "warning")
        assert rule.message != ""
        assert rule.category in ("crash_zone", "syntax", "convention")


def test_crash_zone_rules_present():
    rules = load_safety_rules(RULES_PATH)
    crash_rules = [r for r in rules if r.category == "crash_zone"]
    assert len(crash_rules) >= 3  # At least the known crash APIs


def test_load_rules_file_not_found():
    import pytest
    with pytest.raises(FileNotFoundError):
        load_safety_rules(Path("/nonexistent/rules.yaml"))
