# Check: Impedance Matching — High-Speed Signal Series Resistors
# 检查高速信号网络是否有串联匹配电阻

proc check_impedance_matching {design} {
    # High-speed net name patterns
    set hs_net_patterns {
        {^USB_D[PM+-]}
        {^USB_DP$}
        {^USB_DM$}
        {^LVDS_}
        {^MIPI_}
        {^HDMI_D}
    }

    # High-speed pin name patterns (case-insensitive match)
    set hs_pin_patterns {
        {^DP$}
        {^DM$}
        {^D\+$}
        {^D-$}
    }

    set net_map [build_net_components_map $design]
    set findings [list]

    # Check nets by name pattern
    dict for {net_name components} $net_map {
        set is_hs 0
        foreach pattern $hs_net_patterns {
            if {[regexp -nocase $pattern $net_name]} {
                set is_hs 1
                break
            }
        }

        # Also check if any pin on this net has a high-speed pin name
        if {!$is_hs} {
            foreach comp $components {
                set pin_name [lindex $comp 1]
                foreach pattern $hs_pin_patterns {
                    if {[regexp -nocase $pattern $pin_name]} {
                        set is_hs 1
                        break
                    }
                }
                if {$is_hs} break
            }
        }

        if {!$is_hs} continue

        # Check if net has at least one series resistor
        if {![net_has_component_type $net_name $net_map "R"]} {
            lappend findings [finding \
                "High-speed net '$net_name' has no series matching resistor" \
                "" $net_name ""]
        }
    }

    if {[llength $findings] == 0} {
        check_result "impedance_matching" $::CHECK_P2 "PASS" [list]
    } else {
        check_result "impedance_matching" $::CHECK_P2 "FAIL" $findings
    }
}
