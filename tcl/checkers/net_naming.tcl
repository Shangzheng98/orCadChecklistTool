# Check: Auto-generated Net Names
# 检测自动生成的网络名称（如 N00234），建议赋予有意义的名字

proc check_net_naming {design} {
    # Patterns that indicate auto-generated names
    set forbidden_patterns {
        {^N\d{5,}$}
        {^Net\d+$}
        {^NET_\d+$}
    }

    # Collect power net names to skip them
    set power_nets [list]
    foreach page [GetPages $design] {
        foreach pp [GetPowerPins $page] {
            set net_name [GetPinNet $pp]
            if {$net_name ne "" && [lsearch -exact $power_nets $net_name] < 0} {
                lappend power_nets $net_name
            }
        }
    }

    set findings [list]
    foreach net [GetFlatNets $design] {
        set net_name [GetNetName $net]

        # Skip power nets
        if {[lsearch -exact $power_nets $net_name] >= 0} continue

        foreach pattern $forbidden_patterns {
            if {[regexp $pattern $net_name]} {
                lappend findings [finding \
                    "Net '$net_name' appears auto-generated, consider a meaningful name" \
                    "" $net_name ""]
                break
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "net_naming" $::CHECK_INFO "PASS" [list]
    } else {
        check_result "net_naming" $::CHECK_INFO "FAIL" $findings
    }
}
