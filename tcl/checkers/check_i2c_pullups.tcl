# Check: I2C Pull-up Resistors
# I2C 总线需要上拉电阻，检查 SDA/SCL 网络是否有上拉

proc check_i2c_pullups {design} {
    set findings [list]

    set power_nets [collect_power_net_names $design]
    set net_map [build_net_components_map $design]

    # Find I2C nets by flat net name pattern
    set i2c_nets [list]
    foreach net [GetFlatNets $design] {
        set net_name [GetNetName $net]
        set upper [string toupper $net_name]

        set is_i2c 0
        if {[string match "*SDA*" $upper] || [string match "*SCL*" $upper] ||
            [string match "*I2C*" $upper]} {
            set is_i2c 1
        }

        # Also check pin names on the net
        if {!$is_i2c} {
            foreach pin [GetNetPins $net] {
                set pname [string toupper [GetPinName $pin]]
                if {$pname eq "SDA" || $pname eq "SCL"} {
                    set is_i2c 1
                    break
                }
            }
        }

        if {$is_i2c && [lsearch -exact $i2c_nets $net_name] < 0} {
            lappend i2c_nets $net_name
        }
    }

    # For each I2C net, check for a pull-up resistor connected to a power net
    foreach net_name $i2c_nets {
        if {![dict exists $net_map $net_name]} continue

        set comps [dict get $net_map $net_name]
        set has_pullup 0

        foreach comp $comps {
            set refdes [lindex $comp 0]
            if {![is_resistor $refdes]} continue

            # Check if the resistor also connects to a power net
            # Look through all nets for this resistor
            dict for {other_net other_comps} $net_map {
                if {$other_net eq $net_name} continue
                if {[lsearch -exact $power_nets $other_net] < 0} continue
                foreach other_comp $other_comps {
                    if {[lindex $other_comp 0] eq $refdes} {
                        set has_pullup 1
                        break
                    }
                }
                if {$has_pullup} break
            }
            if {$has_pullup} break
        }

        if {!$has_pullup} {
            lappend findings [finding \
                "I2C net '$net_name' has no pull-up resistor to a power net" \
                "" $net_name ""]
        }
    }

    if {[llength $findings] == 0} {
        check_result "i2c_pullups" $::CHECK_P1 "PASS" [list]
    } else {
        check_result "i2c_pullups" $::CHECK_P1 "FAIL" $findings
    }
}
