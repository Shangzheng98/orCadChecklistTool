# Check: Power Net Voltage Labels
# 电源网络名称应包含电压信息（如 3V3、1V8、5V）

proc check_power_voltage_label {design} {
    set findings [list]

    set power_nets [collect_power_net_names $design]

    # Pattern matching voltage info in net names
    # Matches: 3V3, 1V8, 5V, 12V, 3.3V, 1.8V, +5V, etc.
    set voltage_pattern {(\d+[Vv]\d*|\d+\.\d+[Vv])}

    foreach net_name $power_nets {
        set upper [string toupper $net_name]

        # Skip GND variants - they do not need voltage labels
        if {[regexp -nocase {^(A?GND|DGND|PGND|VSS|GNDA|GNDD)} $upper]} continue

        # Check if the name contains voltage info
        if {[regexp $voltage_pattern $net_name]} continue

        lappend findings [finding \
            "Power net '$net_name' does not contain voltage info (e.g., VCC_3V3, VDD_1V8)" \
            "" $net_name ""]
    }

    if {[llength $findings] == 0} {
        check_result "power_voltage_label" $::CHECK_P1 "PASS" [list]
    } else {
        check_result "power_voltage_label" $::CHECK_P1 "FAIL" $findings
    }
}
