# Check: Decoupling Capacitors
# IC power pins must have at least one decoupling capacitor on the same net

proc check_decoupling_caps {design} {
    set net_map [build_net_components_map $design]
    set power_nets [collect_power_net_names $design]

    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            if {![is_ic $part]} continue

            set refdes [GetPropValue $part "Reference"]
            set part_name [GetPropValue $part "Part Name"]
            set value [GetPropValue $part "Value"]

            # Skip voltage regulators
            set combined "$part_name $value"
            if {[regexp -nocase {REG|LDO} $combined]} continue

            # Check each pin on a power net
            foreach pin [GetPins $part] {
                set pin_net [GetPinNet $pin]
                if {$pin_net eq ""} continue

                # Only check power nets
                if {[lsearch -exact $power_nets $pin_net] < 0} continue

                # Check if there is a capacitor on this net
                if {![net_has_component_type $pin_net $net_map {^C[0-9]}]} {
                    set pin_name [GetPinName $pin]
                    set pin_num [GetPinNumber $pin]
                    lappend findings [finding \
                        "IC '$refdes' power pin ${pin_name}(${pin_num}) on net '$pin_net' has no decoupling capacitor" \
                        $refdes $pin_net $page_name]
                }
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "decoupling_caps" $::CHECK_P0 "PASS" [list]
    } else {
        check_result "decoupling_caps" $::CHECK_P0 "FAIL" $findings
    }
}
