# Check: Unconnected Pins
# 直接在 OrCAD 内检查每个引脚的网络连接状态

proc check_unconnected_pins {design} {
    set ignore_names [list "NC" "N/C" "DNC"]
    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue

            foreach pin [GetPins $part] {
                set pin_name [GetPinName $pin]
                set pin_num  [GetPinNumber $pin]
                set net_name [GetPinNet $pin]

                # Skip NC pins
                set skip 0
                foreach ignore $ignore_names {
                    if {[string toupper $pin_name] eq $ignore} {
                        set skip 1
                        break
                    }
                }
                if {$skip} continue

                # Check if pin has no net
                if {$net_name eq ""} {
                    lappend findings [finding \
                        "Pin '$pin_name' (pin $pin_num) on $refdes has no net" \
                        $refdes "" $page_name]
                }
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "unconnected_pins" $::CHECK_WARNING "PASS" [list]
    } else {
        check_result "unconnected_pins" $::CHECK_WARNING "FAIL" $findings
    }
}
