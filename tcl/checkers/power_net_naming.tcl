# Check: Power Net Naming Convention
# 直接从 OrCAD 获取电源网络，检查命名规范

proc check_power_net_naming {design} {
    # Allowed power net name patterns
    set allowed_patterns {
        {^VCC_.*}
        {^VDD_.*}
        {^GND.*}
        {^VBAT.*}
        {^VIN.*}
        {^AVCC.*}
        {^AVDD.*}
        {^AGND.*}
        {^V\d+V\d*.*}
    }

    # Collect power net names from power pins
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
    foreach net_name $power_nets {
        set matched 0
        foreach pattern $allowed_patterns {
            if {[regexp $pattern $net_name]} {
                set matched 1
                break
            }
        }
        if {!$matched} {
            lappend findings [finding \
                "Power net '$net_name' does not match naming convention" \
                "" $net_name ""]
        }
    }

    if {[llength $findings] == 0} {
        check_result "power_net_naming" $::CHECK_WARNING "PASS" [list]
    } else {
        check_result "power_net_naming" $::CHECK_WARNING "FAIL" $findings
    }
}
