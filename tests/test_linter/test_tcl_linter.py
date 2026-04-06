from orcad_checker.linter.tcl_linter import lint_tcl, LintReport


def test_clean_checker_passes():
    code = """
proc check_example {design} {
    set findings [list]
    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
        }
    }
    if {[llength $findings] == 0} {
        check_result "example" $::CHECK_P1 "PASS" [list]
    } else {
        check_result "example" $::CHECK_P1 "FAIL" $findings
    }
}
"""
    report = lint_tcl(code)
    assert report.passed is True
    assert report.fatal_count == 0
    assert report.error_count == 0


def test_crash_zone_fails_lint():
    code = """
proc check_bad {design} {
    set findings [list]
    set iter [DboFlatNet_NewPortOccurrencesIter $net $st]
    check_result "bad" $::CHECK_P1 "PASS" [list]
}
"""
    report = lint_tcl(code)
    assert report.passed is False
    assert report.fatal_count >= 1


def test_warnings_dont_fail_lint():
    code = """
proc check_ok {design} {
    set findings [list]
    package require tls
    check_result "ok" $::CHECK_P1 "PASS" [list]
}
"""
    report = lint_tcl(code)
    assert report.passed is True  # warnings don't fail
    assert report.warning_count >= 1


def test_report_has_summary():
    code = "DboFlatNet_NewPortOccurrencesIter"
    report = lint_tcl(code, require_checker=False)
    assert isinstance(report.summary, str)
    assert len(report.summary) > 0


def test_lint_non_checker_code():
    code = """
proc helper {x} {
    return $x
}
"""
    report = lint_tcl(code, require_checker=False)
    assert report.passed is True


def test_report_to_dict():
    code = "set x 1"
    report = lint_tcl(code, require_checker=False)
    d = report.to_dict()
    assert "passed" in d
    assert "issues" in d
    assert "summary" in d
