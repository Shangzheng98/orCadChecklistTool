from orcad_checker.linter.template_checker import check_template_compliance, TemplateIssue


def test_valid_checker_passes():
    code = """
proc check_my_rule {design} {
    set findings [list]
    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} {
                lappend findings [finding "Missing refdes" $refdes "" $page_name]
            }
        }
    }
    if {[llength $findings] == 0} {
        check_result "my_rule" $::CHECK_P1 "PASS" [list]
    } else {
        check_result "my_rule" $::CHECK_P1 "FAIL" $findings
    }
}
"""
    issues = check_template_compliance(code)
    assert len(issues) == 0


def test_missing_proc_signature():
    code = """
set findings [list]
foreach page [GetPages $design] {
    puts "hello"
}
check_result "my_rule" $::CHECK_P1 "PASS" [list]
"""
    issues = check_template_compliance(code)
    assert any("proc check_" in i.message for i in issues)


def test_missing_check_result():
    code = """
proc check_my_rule {design} {
    set findings [list]
    foreach page [GetPages $design] {
        puts "ok"
    }
}
"""
    issues = check_template_compliance(code)
    assert any("check_result" in i.message for i in issues)


def test_missing_findings_list():
    code = """
proc check_my_rule {design} {
    foreach page [GetPages $design] {
        puts "ok"
    }
    check_result "my_rule" $::CHECK_P1 "PASS" [list]
}
"""
    issues = check_template_compliance(code)
    assert any("findings" in i.message for i in issues)


def test_missing_design_parameter():
    code = """
proc check_my_rule {} {
    set findings [list]
    check_result "my_rule" $::CHECK_P1 "PASS" [list]
}
"""
    issues = check_template_compliance(code)
    assert any("design" in i.message for i in issues)


def test_non_checker_code_skips_template_check():
    code = """
proc helper_function {x y} {
    return [expr {$x + $y}]
}
"""
    issues = check_template_compliance(code, require_checker=False)
    assert len(issues) == 0
