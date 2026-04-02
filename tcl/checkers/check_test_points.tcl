# Check: Test Point Coverage
# 关键信号网络（电源、时钟、通信总线）应有测试点

proc check_test_points {design} {
    set findings [list]

    set net_map [build_net_components_map $design]
    set power_nets [collect_power_net_names $design]

    # Collect nets that already have test points
    set nets_with_tp [list]
    dict for {net_name comps} $net_map {
        foreach comp $comps {
            if {[is_test_point [lindex $comp 0]]} {
                if {[lsearch -exact $nets_with_tp $net_name] < 0} {
                    lappend nets_with_tp $net_name
                }
                break
            }
        }
    }

    # Check power rail nets have test points (skip GND variants)
    foreach pn $power_nets {
        if {[regexp -nocase {^(A?GND|DGND|PGND|VSS)} $pn]} continue
        if {[lsearch -exact $nets_with_tp $pn] < 0} {
            lappend findings [finding \
                "Power net '$pn' has no test point" \
                "" $pn ""]
        }
    }

    # Check clock and communication nets
    set comm_patterns [list "*CLK*" "*SDA*" "*SCL*" "*TX*" "*RX*" \
        "*MOSI*" "*MISO*" "*SCLK*"]

    dict for {net_name comps} $net_map {
        # Skip power nets (already checked above)
        if {[lsearch -exact $power_nets $net_name] >= 0} continue

        set upper [string toupper $net_name]
        set needs_tp 0
        foreach pat $comm_patterns {
            if {[string match $pat $upper]} {
                set needs_tp 1
                break
            }
        }

        if {$needs_tp && [lsearch -exact $nets_with_tp $net_name] < 0} {
            lappend findings [finding \
                "Signal net '$net_name' has no test point" \
                "" $net_name ""]
        }
    }

    if {[llength $findings] == 0} {
        check_result "test_points" $::CHECK_P1 "PASS" [list]
    } else {
        check_result "test_points" $::CHECK_P1 "FAIL" $findings
    }
}
