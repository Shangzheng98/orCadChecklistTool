"""Golden design tests: a design with known issues that checkers MUST detect.

This serves as a regression test to verify checker accuracy. Any new checker
or modification must not break these known-good detections.
"""
from pathlib import Path

import pytest

from orcad_checker.parser.design_parser import parse_design_file
from orcad_checker.engine.runner import run_checks

GOLDEN_PATH = Path(__file__).parent.parent / "fixtures" / "golden_test_design.json"


@pytest.fixture
def golden_design():
    return parse_design_file(GOLDEN_PATH)


def test_golden_design_loads(golden_design):
    assert golden_design.design_name == "GoldenTestBoard"
    assert len(golden_design.components) > 0
    assert len(golden_design.nets) > 0


def test_detects_duplicate_refdes(golden_design):
    report = run_checks(golden_design, selected_checkers=["duplicate_refdes"])
    fail_results = [r for r in report.results if r.status.value == "FAIL"]
    assert len(fail_results) == 1
    findings_text = " ".join(f.message for f in fail_results[0].findings)
    assert "R1" in findings_text


def test_detects_missing_attributes(golden_design):
    report = run_checks(golden_design, selected_checkers=["missing_attributes"])
    fail_results = [r for r in report.results if r.status.value == "FAIL"]
    assert len(fail_results) == 1
    findings_text = " ".join(f.message for f in fail_results[0].findings)
    assert "U3" in findings_text


def test_detects_unconnected_pins(golden_design):
    report = run_checks(golden_design, selected_checkers=["unconnected_pins"])
    fail_results = [r for r in report.results if r.status.value == "FAIL"]
    assert len(fail_results) == 1


def test_detects_single_pin_nets(golden_design):
    report = run_checks(golden_design, selected_checkers=["single_pin_nets"])
    fail_results = [r for r in report.results if r.status.value == "FAIL"]
    assert len(fail_results) == 1
    findings_text = " ".join(f.message for f in fail_results[0].findings)
    assert "ORPHAN_NET" in findings_text


def test_clean_rules_pass(golden_design):
    """Power net naming and net naming should pass on golden design."""
    report = run_checks(golden_design, selected_checkers=["power_net_naming"])
    pass_results = [r for r in report.results if r.status.value == "PASS"]
    assert len(pass_results) == 1
