# Check: Single Pin Nets
# 检测只连接了一个引脚的网络（通常是接线遗漏）

proc check_single_pin_nets {design} {
    # Collect power nets to skip
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

        set pins [GetNetPins $net]
        if {[llength $pins] == 1} {
            set pin [lindex $pins 0]
            set refdes [GetPinRefDes $pin]
            set pin_num [GetPinNumber $pin]
            lappend findings [finding \
                "Net '$net_name' has only one connection: $refdes pin $pin_num" \
                $refdes $net_name ""]
        }
    }

    if {[llength $findings] == 0} {
        check_result "single_pin_nets" $::CHECK_WARNING "PASS" [list]
    } else {
        check_result "single_pin_nets" $::CHECK_WARNING "FAIL" $findings
    }
}
