# Extract net data from OrCAD Capture design

proc extract_nets {design power_net_names} {
    set nets [list]
    set unconnected_pins [list]

    set flat_nets [GetFlatNets $design]
    foreach net $flat_nets {
        set net_name [GetNetName $net]
        set is_power 0
        if {[lsearch -exact $power_net_names $net_name] >= 0} {
            set is_power 1
        }

        set connections [list]
        set net_pins [GetNetPins $net]
        foreach pin $net_pins {
            set refdes [GetPinRefDes $pin]
            set pin_number [GetPinNumber $pin]
            set pin_name [GetPinName $pin]

            lappend connections [dict create \
                refdes $refdes \
                pin_number $pin_number \
                pin_name $pin_name \
            ]
        }

        # Track unconnected (single-pin) nets
        if {[llength $connections] == 0} {
            continue
        }

        lappend nets [dict create \
            name $net_name \
            is_power $is_power \
            connections $connections \
        ]
    }

    return [dict create nets $nets unconnected_pins $unconnected_pins]
}
