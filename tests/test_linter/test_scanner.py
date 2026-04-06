from orcad_checker.linter.scanner import scan_tcl_code, LintIssue


# --- Crash zone detection ---

def test_detects_fatal_crash_api():
    code = """
proc get_net_pins {net} {
    set st [DboState]
    set iter [DboFlatNet_NewPortOccurrencesIter $net $st]
    return $iter
}
"""
    issues = scan_tcl_code(code)
    fatal = [i for i in issues if i.severity == "fatal"]
    assert len(fatal) >= 1
    assert "DboFlatNet_NewPortOccurrencesIter" in fatal[0].matched_text


def test_detects_multiple_crash_apis():
    code = """
set iter [DboFlatNet_NewPortOccurrencesIter $net $st]
set port [DboFlatNetPortOccurrencesIter_NextPortOccurrence $iter $st]
set ref [DboInstOccurrence_sGetReferenceDesignator $port $st]
"""
    issues = scan_tcl_code(code)
    fatal = [i for i in issues if i.severity == "fatal"]
    assert len(fatal) == 3


def test_safe_code_no_fatal():
    code = """
proc check_example {design} {
    set findings [list]
    foreach page [GetPages $design] {
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
        }
    }
    check_result "example" $::CHECK_P1 "PASS" [list]
}
"""
    issues = scan_tcl_code(code)
    fatal = [i for i in issues if i.severity == "fatal"]
    assert len(fatal) == 0


# --- Syntax hazard detection ---

def test_detects_brace_in_comment():
    code = """
proc foo {} {
    # Split by },{ to find objects
    puts "hello"
}
"""
    issues = scan_tcl_code(code)
    syntax = [i for i in issues if i.category == "syntax"]
    assert len(syntax) >= 1


def test_detects_array_confusion():
    code = '''
set msg "pin $pin_name($pin_num) is bad"
'''
    issues = scan_tcl_code(code)
    syntax = [i for i in issues if i.category == "syntax"]
    assert len(syntax) >= 1


# --- Convention warnings ---

def test_detects_package_require_tls():
    code = "package require tls"
    issues = scan_tcl_code(code)
    conv = [i for i in issues if i.category == "convention"]
    assert len(conv) >= 1


def test_detects_destroy_root():
    code = "destroy ."
    issues = scan_tcl_code(code)
    conv = [i for i in issues if i.category == "convention"]
    assert len(conv) >= 1


# --- Line number tracking ---

def test_issue_has_line_number():
    code = "line1\nline2\nDboFlatNet_NewPortOccurrencesIter\nline4"
    issues = scan_tcl_code(code)
    assert issues[0].line == 3
