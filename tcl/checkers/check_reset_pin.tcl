# Check: Reset Pin Protection
# IC 复位引脚需要上拉电阻和滤波电容

proc check_reset_pin {design} {
    set findings [list]

    set power_nets [collect_power_net_names $design]
    set net_map [build_net_components_map $design]

    # Classify power nets into VCC-like and GND-like
    set vcc_nets [list]
    set gnd_nets [list]
    foreach pn $power_nets {
        if {[regexp -nocase {^(A?GND|DGND|PGND|VSS)} $pn]} {
            lappend gnd_nets $pn
        } else {
            lappend vcc_nets $pn
        }
    }

    # Find IC reset pins
    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue
            if {![is_ic $part]} continue

            foreach pin [GetPins $part] {
                set pin_name [string toupper [GetPinName $pin]]
                set net_name [GetPinNet $pin]

                if {$net_name eq ""} continue
                if {![string match "*RST*" $pin_name] &&
                    ![string match "*RESET*" $pin_name]} continue

                # Check for pull-up resistor (R to VCC) and filter cap (C to GND)
                set has_pullup 0
                set has_cap 0

                if {[dict exists $net_map $net_name]} {
                    foreach comp [dict get $net_map $net_name] {
                        set comp_ref [lindex $comp 0]

                        # Check pull-up resistor
                        if {!$has_pullup && [is_resistor $comp_ref]} {
                            dict for {other_net other_comps} $net_map {
                                if {$other_net eq $net_name} continue
                                if {[lsearch -exact $vcc_nets $other_net] < 0} continue
                                foreach oc $other_comps {
                                    if {[lindex $oc 0] eq $comp_ref} {
                                        set has_pullup 1
                                        break
                                    }
                                }
                                if {$has_pullup} break
                            }
                        }

                        # Check filter capacitor
                        if {!$has_cap && [is_capacitor $comp_ref]} {
                            dict for {other_net other_comps} $net_map {
                                if {$other_net eq $net_name} continue
                                if {[lsearch -exact $gnd_nets $other_net] < 0} continue
                                foreach oc $other_comps {
                                    if {[lindex $oc 0] eq $comp_ref} {
                                        set has_cap 1
                                        break
                                    }
                                }
                                if {$has_cap} break
                            }
                        }

                        if {$has_pullup && $has_cap} break
                    }
                }

                set issues [list]
                if {!$has_pullup} {
                    lappend issues "no pull-up resistor"
                }
                if {!$has_cap} {
                    lappend issues "no filter capacitor"
                }
                if {[llength $issues] > 0} {
                    lappend findings [finding \
                        "Reset pin '$pin_name' on $refdes (net '$net_name'): [join $issues { and }]" \
                        $refdes $net_name $page_name]
                }
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "reset_pin" $::CHECK_P1 "PASS" [list]
    } else {
        check_result "reset_pin" $::CHECK_P1 "FAIL" $findings
    }
}
