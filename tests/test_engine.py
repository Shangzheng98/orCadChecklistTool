from pathlib import Path

from orcad_checker.engine.registry import discover_checkers, list_checkers
from orcad_checker.engine.rule_loader import load_rules
from orcad_checker.engine.runner import run_checks

RULES_PATH = Path(__file__).parent.parent / "rules" / "default_rules.yaml"


def test_discover_checkers():
    discover_checkers()
    checkers = list_checkers()
    assert "duplicate_refdes" in checkers
    assert "missing_attributes" in checkers


def test_load_rules():
    rules = load_rules(RULES_PATH)
    assert "duplicate_refdes" in rules
    assert rules["duplicate_refdes"]["severity"] == "error"


def test_load_rules_nonexistent():
    rules = load_rules("/nonexistent/rules.yaml")
    assert rules == {}


def test_load_rules_none():
    rules = load_rules(None)
    assert rules == {}


def test_run_checks(sample_design):
    report = run_checks(sample_design)
    assert report.design_name == "TestBoard"
    assert report.result_id
    assert len(report.results) > 0


def test_run_selected_checkers(sample_design):
    report = run_checks(sample_design, selected_checkers=["duplicate_refdes"])
    assert report.summary.total_checks == 1
    rule_ids = {r.rule_id for r in report.results}
    assert "duplicate_refdes" in rule_ids
    assert "missing_attributes" not in rule_ids


def test_run_with_rules(sample_design):
    report = run_checks(sample_design, rules_path=str(RULES_PATH))
    assert report.summary.total_checks >= 2
