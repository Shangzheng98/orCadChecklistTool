# Check: Crystal Load Capacitors
# 晶振信号引脚需要负载电容连接到 GND

proc check_crystal_load_caps {design} {
    set findings [list]

    set net_map [build_net_components_map $design]

    # Collect GND net names
    set gnd_nets [list]
    set power_nets [collect_power_net_names $design]
    foreach pn $power_nets {
        if {[regexp -nocase {^(A?GND|DGND|PGND|VSS)} $pn]} {
            lappend gnd_nets $pn
        }
    }

    # Find crystal parts: refdes ^Y or ^X, or Part Name containing crystal/XTAL
    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue

            set is_crystal 0
            if {[regexp {^[YX]\d} $refdes]} {
                set is_crystal 1
            }
            if {!$is_crystal} {
                set part_name [string toupper [GetPropValue $part "Part Name"]]
                if {[string match "*CRYSTAL*" $part_name] ||
                    [string match "*XTAL*" $part_name]} {
                    set is_crystal 1
                }
            }
            if {!$is_crystal} continue

            # Check each signal pin of the crystal
            foreach pin [GetPins $part] {
                set pin_name [GetPinName $pin]
                set pin_num  [GetPinNumber $pin]
                set net_name [GetPinNet $pin]

                if {$net_name eq ""} continue

                # Skip GND/power pins on the crystal itself
                set upper_pin [string toupper $pin_name]
                if {$upper_pin eq "GND" || $upper_pin eq "CASE" ||
                    $upper_pin eq "VSS"} continue

                # Check this net has a capacitor also connected to GND
                set has_load_cap 0
                if {[dict exists $net_map $net_name]} {
                    foreach comp [dict get $net_map $net_name] {
                        set comp_ref [lindex $comp 0]
                        if {![is_capacitor $comp_ref]} continue

                        # Check if this cap also connects to a GND net
                        dict for {other_net other_comps} $net_map {
                            if {$other_net eq $net_name} continue
                            if {[lsearch -exact $gnd_nets $other_net] < 0} continue
                            foreach oc $other_comps {
                                if {[dict get $oc refdes] eq $comp_ref} {
                                    set has_load_cap 1
                                    break
                                }
                            }
                            if {$has_load_cap} break
                        }
                        if {$has_load_cap} break
                    }
                }

                if {!$has_load_cap} {
                    lappend findings [finding \
                        "Crystal $refdes pin '$pin_name' (net '$net_name') missing load capacitor to GND" \
                        $refdes $net_name $page_name]
                }
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "crystal_load_caps" $::CHECK_P1 "PASS" [list]
    } else {
        check_result "crystal_load_caps" $::CHECK_P1 "FAIL" $findings
    }
}
