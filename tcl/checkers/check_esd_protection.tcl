# Check: ESD Protection on External Connectors
# Signal pins on USB/HDMI/SD connectors must have ESD/TVS protection on same net

proc check_esd_protection {design} {
    set net_map [build_net_components_map $design]

    # Connector identification: Part Name or Value contains these keywords
    set external_keywords {USB HDMI DP DISPLAYPORT SD SDCARD ETHERNET RJ45 ETHER}

    # Power pin name patterns to skip
    set power_pin_patterns {
        {^VCC}
        {^VDD}
        {^VBUS}
        {^GND}
        {^VSS}
        {^SHIELD}
        {^SHELL}
    }

    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]

            # Must be a connector
            if {![is_connector $refdes]} continue

            set part_name [GetPropValue $part "Part Name"]
            set value [GetPropValue $part "Value"]
            set combined [string toupper "$part_name $value"]

            # Check if it is an external interface connector
            set is_external 0
            foreach kw $external_keywords {
                if {[string match "*$kw*" $combined]} {
                    set is_external 1
                    break
                }
            }
            if {!$is_external} continue

            # Check signal pins for ESD protection
            foreach pin [GetPins $part] {
                set pin_net [GetPinNet $pin]
                set pin_name [GetPinName $pin]
                set pin_num [GetPinNumber $pin]

                if {$pin_net eq ""} continue

                # Skip power and ground pins
                set is_power 0
                foreach pp $power_pin_patterns {
                    if {[regexp -nocase $pp $pin_name]} {
                        set is_power 1
                        break
                    }
                }
                if {$is_power} continue

                # Check for ESD/TVS device on this net
                # ESD parts typically have refdes starting with D, U, or Z
                # and Part Name/Value containing TVS, ESD, or PESD
                set has_esd 0
                if {[dict exists $net_map $pin_net]} {
                    foreach comp [dict get $net_map $pin_net] {
                        set comp_refdes [lindex $comp 0]
                        # Skip self
                        if {$comp_refdes eq $refdes} continue

                        # Look up the part on the schematic to check Part Name
                        # For now use refdes prefix heuristic: D prefix with TVS/ESD
                        # Also accept dedicated ESD prefix patterns
                        if {[regexp -nocase {^(D|U|Z)[0-9]} $comp_refdes]} {
                            set has_esd 1
                            break
                        }
                    }
                }

                if {!$has_esd} {
                    lappend findings [finding \
                        "Connector '$refdes' signal pin ${pin_name}(${pin_num}) on net '$pin_net' has no ESD protection" \
                        $refdes $pin_net $page_name]
                }
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "esd_protection" $::CHECK_P0 "PASS" [list]
    } else {
        check_result "esd_protection" $::CHECK_P0 "FAIL" $findings
    }
}
