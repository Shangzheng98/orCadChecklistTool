# Check: Unused Pin Handling
# IC input pins must not be left floating (unconnected and not marked NC/DNC)

proc check_unused_pin_handling {design} {
    # Pin name patterns that suggest input function
    set input_patterns {
        {^IN}
        {^DIN}
        {^D[0-9]}
        {^A[0-9]}
        {^SDA}
        {^SCL}
        {^MOSI}
        {^MISO}
        {^CLK}
        {^CS}
        {^EN}
        {^ENABLE}
        {^RST}
        {^RESET}
        {^RXD}
        {^RX}
        {^SDIN}
        {^WR}
        {^RD}
        {^OE}
        {^CE}
    }

    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            if {![is_ic $part]} continue

            set refdes [GetPropValue $part "Reference"]

            foreach pin [GetPins $part] {
                set pin_net [GetPinNet $pin]
                set pin_name [GetPinName $pin]
                set pin_num [GetPinNumber $pin]
                set pin_type [GetPinType $pin]

                # Skip pins that are connected
                if {$pin_net ne ""} continue

                # Skip pins explicitly marked NC or DNC
                set name_upper [string toupper $pin_name]
                if {$name_upper eq "NC" || $name_upper eq "DNC"} continue
                if {[regexp -nocase {^N\.?C\.?$} $pin_name]} continue

                # Detect input pins by type or name heuristics
                set is_input 0

                # Check pin type if available
                set type_upper [string toupper $pin_type]
                if {$type_upper eq "INPUT" || $type_upper eq "IN" || $type_upper eq "BIDIRECTIONAL" || $type_upper eq "BIDI"} {
                    set is_input 1
                }

                # Check pin name heuristics
                if {!$is_input} {
                    foreach pattern $input_patterns {
                        if {[regexp -nocase $pattern $pin_name]} {
                            set is_input 1
                            break
                        }
                    }
                }

                if {$is_input} {
                    lappend findings [finding \
                        "IC '$refdes' input pin ${pin_name}(${pin_num}) is unconnected and not marked NC" \
                        $refdes "" $page_name]
                }
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "unused_pin_handling" $::CHECK_P0 "PASS" [list]
    } else {
        check_result "unused_pin_handling" $::CHECK_P0 "FAIL" $findings
    }
}
