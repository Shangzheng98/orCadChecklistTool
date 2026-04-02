# Check: Thermal Pad Connectivity
# 检查散热焊盘是否正确连接到GND或电源网络

proc check_thermal_pad {design} {
    # Pin name patterns for thermal/exposed pads (case-insensitive)
    set thermal_patterns {
        {^EP$}
        {^EPAD$}
        {^PAD$}
        {^Exposed}
        {^THERMAL$}
        {^PowerPAD$}
        {^TAB$}
        {^SLUG$}
        {^GND_PAD$}
    }

    set power_nets [collect_power_net_names $design]
    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue

            # Only check ICs and regulators (skip passives and connectors)
            if {![is_ic $part]} continue

            foreach pin [GetPins $part] {
                set pin_name [GetPinName $pin]
                set pin_num  [GetPinNumber $pin]
                set net_name [GetPinNet $pin]

                # Check if this is a thermal pad pin
                set is_thermal 0
                foreach pattern $thermal_patterns {
                    if {[regexp -nocase $pattern $pin_name]} {
                        set is_thermal 1
                        break
                    }
                }
                if {!$is_thermal} continue

                # Thermal pad must be connected to some net
                if {$net_name eq ""} {
                    lappend findings [finding \
                        "Thermal pad '$pin_name' (pin $pin_num) on $refdes is unconnected" \
                        $refdes "" $page_name]
                    continue
                }

                # Check if connected to GND or a power net
                set is_gnd [regexp -nocase {^A?GND} $net_name]
                set is_power [expr {[lsearch -exact $power_nets $net_name] >= 0}]

                if {!$is_gnd && !$is_power} {
                    lappend findings [finding \
                        "Thermal pad '$pin_name' on $refdes connected to '$net_name' (expected GND or power)" \
                        $refdes $net_name $page_name]
                }
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "thermal_pad" $::CHECK_P2 "PASS" [list]
    } else {
        check_result "thermal_pad" $::CHECK_P2 "FAIL" $findings
    }
}
