# Extract power net information from OrCAD Capture design

proc extract_power_nets {design} {
    set power_nets [list]

    # Get power symbols/ports from the design
    set pages [GetPages $design]
    foreach page $pages {
        set power_parts [GetPowerPins $page]
        foreach pp $power_parts {
            set net_name [GetPinNet $pp]
            if {$net_name ne "" && [lsearch -exact $power_nets $net_name] < 0} {
                lappend power_nets $net_name
            }
        }
    }

    return $power_nets
}
