"""Test that the agent pipeline integrates linting."""
from orcad_checker.ai.tcl_agent import extract_and_lint_tcl


def test_extract_and_lint_safe_code():
    response = """Here is a checker:
```tcl
proc check_example {design} {
    set findings [list]
    check_result "example" $::CHECK_P1 "PASS" [list]
}
```
"""
    code, lint_report = extract_and_lint_tcl(response)
    assert code != ""
    assert lint_report.passed is True


def test_extract_and_lint_dangerous_code():
    response = """Here is a checker:
```tcl
proc check_bad {design} {
    set findings [list]
    set iter [DboFlatNet_NewPortOccurrencesIter $net $st]
    check_result "bad" $::CHECK_P1 "PASS" [list]
}
```
"""
    code, lint_report = extract_and_lint_tcl(response)
    assert code != ""
    assert lint_report.passed is False
    assert lint_report.fatal_count >= 1


def test_extract_no_code():
    response = "I can help you with that. What would you like to check?"
    code, lint_report = extract_and_lint_tcl(response)
    assert code == ""
    assert lint_report is None
