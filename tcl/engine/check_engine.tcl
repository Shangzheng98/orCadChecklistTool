# ============================================================================
# OrCAD Capture TCL Check Engine
# ============================================================================

# Priority levels: P0=critical, P1=serious, P2=moderate, P3=info
set ::CHECK_P0 "P0"
set ::CHECK_P1 "P1"
set ::CHECK_P2 "P2"
set ::CHECK_P3 "P3"

# Legacy aliases
set ::CHECK_ERROR   "P0"
set ::CHECK_WARNING "P1"
set ::CHECK_INFO    "P2"

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
    catch {clear_checker_cache}
}

# ── Check Runner ─────────────────────────────────────────────

proc run_all_checks {{checker_list ""} {design ""}} {
    if {$design eq ""} {
        set design [GetActiveDesign]
        if {$design eq ""} {
            puts "ERROR: No active design open."
            return
        }
    }

    clear_results

    # Default: run all checkers
    if {$checker_list eq ""} {
        set checker_list {
            check_duplicate_refdes
            check_footprint_validation
            check_decoupling_caps
            check_unused_pin_handling
            check_esd_protection
            check_missing_attributes
            check_unconnected_pins
            check_power_net_naming
            check_single_pin_nets
            check_i2c_pullups
            check_crystal_load_caps
            check_reset_pin
            check_test_points
            check_power_voltage_label
            check_net_naming
            check_impedance_matching
            check_standard_values
            check_thermal_pad
            check_connector_pinout
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

proc _priority_label {sev} {
    switch $sev {
        "P0" { return "P0-Critical" }
        "P1" { return "P1-Serious" }
        "P2" { return "P2-Moderate" }
        "P3" { return "P3-Info" }
        default { return $sev }
    }
}

proc print_results {} {
    set p0 0; set p1 0; set p2 0; set p3 0; set passes 0

    foreach result $::check_results {
        set status [dict get $result status]
        set severity [dict get $result severity]
        if {$status eq "PASS"} {
            incr passes
        } else {
            switch $severity {
                "P0" { incr p0 }
                "P1" { incr p1 }
                "P2" { incr p2 }
                "P3" { incr p3 }
            }
        }
    }

    puts ""
    puts [string repeat "=" 60]
    puts "Summary: [llength $::check_results] checks | PASS=$passes P0=$p0 P1=$p1 P2=$p2 P3=$p3"
    puts [string repeat "=" 60]

    foreach result $::check_results {
        set rid  [dict get $result rule_id]
        set sev  [dict get $result severity]
        set stat [dict get $result status]
        set findings [dict get $result findings]
        set plabel [_priority_label $sev]

        if {$stat eq "PASS"} {
            puts "\[PASS\] \[$plabel\] $rid"
        } else {
            puts "\[FAIL\] \[$plabel\] $rid"
            foreach f $findings {
                puts "       - [dict get $f message]"
            }
        }
    }
}
