# ============================================================================
# OrCAD Capture TCL Check Engine
# 所有检查直接在 OrCAD 内部执行，无需导出 JSON
# ============================================================================

# Result severity levels
set ::CHECK_ERROR   "ERROR"
set ::CHECK_WARNING "WARNING"
set ::CHECK_INFO    "INFO"

# Global result storage
set ::check_results [list]

# ── Result Helpers ───────────────────────────────────────────

proc check_result {rule_id severity status findings} {
    lappend ::check_results [dict create \
        rule_id  $rule_id \
        severity $severity \
        status   $status \
        findings $findings \
    ]
}

proc finding {message {refdes ""} {net ""} {page ""}} {
    return [dict create message $message refdes $refdes net $net page $page]
}

proc clear_results {} {
    set ::check_results [list]
}

# ── Check Runner ─────────────────────────────────────────────

proc run_all_checks {{checker_list ""}} {
    set design [GetActiveDesign]
    if {$design eq ""} {
        puts "ERROR: No active design open."
        return
    }

    clear_results

    # Default: run all checkers
    if {$checker_list eq ""} {
        set checker_list {
            check_duplicate_refdes
            check_missing_attributes
            check_unconnected_pins
            check_footprint_validation
            check_power_net_naming
            check_net_naming
            check_single_pin_nets
        }
    }

    set design_name [GetDesignName $design]
    puts "Running checks on: $design_name"
    puts [string repeat "-" 60]

    foreach checker $checker_list {
        if {[catch {$checker $design} err]} {
            puts "  ERROR running $checker: $err"
        }
    }

    # Print summary
    print_results
    return $::check_results
}

proc run_single_check {checker_name} {
    set design [GetActiveDesign]
    if {$design eq ""} {
        puts "ERROR: No active design open."
        return
    }
    clear_results
    if {[catch {$checker_name $design} err]} {
        puts "ERROR running $checker_name: $err"
    }
    print_results
    return $::check_results
}

# ── Result Printer ───────────────────────────────────────────

proc print_results {} {
    set errors 0
    set warnings 0
    set infos 0
    set passes 0

    foreach result $::check_results {
        set status [dict get $result status]
        set severity [dict get $result severity]
        if {$status eq "PASS"} {
            incr passes
        } else {
            switch $severity {
                "ERROR"   { incr errors }
                "WARNING" { incr warnings }
                "INFO"    { incr infos }
            }
        }
    }

    puts ""
    puts [string repeat "=" 60]
    puts "Summary: [llength $::check_results] checks | PASS=$passes ERROR=$errors WARNING=$warnings INFO=$infos"
    puts [string repeat "=" 60]

    foreach result $::check_results {
        set rid  [dict get $result rule_id]
        set sev  [dict get $result severity]
        set stat [dict get $result status]
        set findings [dict get $result findings]

        if {$stat eq "PASS"} {
            puts "\[PASS\] \[$sev\] $rid"
        } else {
            puts "\[FAIL\] \[$sev\] $rid"
            foreach f $findings {
                puts "       - [dict get $f message]"
            }
        }
    }
}
