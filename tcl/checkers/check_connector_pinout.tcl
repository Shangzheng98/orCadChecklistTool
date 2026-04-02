# Check: Connector Pinout Validation
# 检查USB等标准连接器引脚分配是否正确

proc check_connector_pinout {design} {
    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue

            # Only check connectors
            if {![is_connector $refdes]} continue

            set part_name [GetPropValue $part "Part Name"]
            set part_upper [string toupper $part_name]

            # Detect connector type and validate
            if {[string match "*TYPE-C*" $part_upper] || \
                [string match "*USB-C*" $part_upper] || \
                [string match "*TYPEC*" $part_upper]} {
                set results [validate_usb_typec $part $refdes $page_name]
                foreach f $results { lappend findings $f }
            } elseif {[string match "*USB*" $part_upper]} {
                set results [validate_usb_standard $part $refdes $page_name]
                foreach f $results { lappend findings $f }
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "connector_pinout" $::CHECK_P2 "PASS" [list]
    } else {
        check_result "connector_pinout" $::CHECK_P2 "FAIL" $findings
    }
}

# Validate USB Type-C connector pinout
proc validate_usb_typec {part refdes page_name} {
    set findings [list]

    # Build pin map: pin_name -> net_name
    set pin_map [dict create]
    foreach pin [GetPins $part] {
        set pin_name [string toupper [GetPinName $pin]]
        set net_name [GetPinNet $pin]
        dict set pin_map $pin_name $net_name
    }

    # Check VBUS pins connect to VBUS net
    foreach vpin {VBUS VBUS1 VBUS2 VBUS3 VBUS4} {
        if {[dict exists $pin_map $vpin]} {
            set net [dict get $pin_map $vpin]
            if {$net eq ""} {
                lappend findings [finding \
                    "$refdes: $vpin pin is unconnected (expected VBUS)" \
                    $refdes "" $page_name]
            } elseif {![regexp -nocase {VBUS} $net]} {
                lappend findings [finding \
                    "$refdes: $vpin connected to '$net' (expected VBUS net)" \
                    $refdes $net $page_name]
            }
        }
    }

    # Check GND pins connect to GND
    foreach gpin {GND GND1 GND2 GND3 GND4 SHIELD} {
        if {[dict exists $pin_map $gpin]} {
            set net [dict get $pin_map $gpin]
            if {$net ne "" && ![regexp -nocase {GND} $net]} {
                lappend findings [finding \
                    "$refdes: $gpin connected to '$net' (expected GND)" \
                    $refdes $net $page_name]
            }
        }
    }

    # Check CC1 and CC2 are on separate nets
    set cc1_net ""
    set cc2_net ""
    if {[dict exists $pin_map "CC1"]} {
        set cc1_net [dict get $pin_map "CC1"]
    }
    if {[dict exists $pin_map "CC2"]} {
        set cc2_net [dict get $pin_map "CC2"]
    }
    if {$cc1_net ne "" && $cc2_net ne "" && $cc1_net eq $cc2_net} {
        lappend findings [finding \
            "$refdes: CC1 and CC2 share the same net '$cc1_net' (must be separate)" \
            $refdes $cc1_net $page_name]
    }

    return $findings
}

# Validate standard USB (Type-A/B) connector pinout
proc validate_usb_standard {part refdes page_name} {
    set findings [list]

    # Standard USB: pin1=VBUS, pin2=D-, pin3=D+, pin4=GND
    set expected_pins [dict create \
        "1" {VBUS  {VBUS VCC}} \
        "2" {D-    {USB_D- USB_DM DM D-}} \
        "3" {D+    {USB_D+ USB_DP DP D+}} \
        "4" {GND   {GND DGND}} \
    ]

    # Build pin number -> net map
    set num_map [dict create]
    foreach pin [GetPins $part] {
        set pin_num [GetPinNumber $pin]
        set net_name [GetPinNet $pin]
        dict set num_map $pin_num $net_name
    }

    dict for {pin_num spec} $expected_pins {
        set signal_name [lindex $spec 0]
        set valid_nets  [lindex $spec 1]

        if {![dict exists $num_map $pin_num]} continue
        set actual_net [dict get $num_map $pin_num]

        if {$actual_net eq ""} {
            lappend findings [finding \
                "$refdes: pin $pin_num ($signal_name) is unconnected" \
                $refdes "" $page_name]
            continue
        }

        # Check if actual net matches any expected pattern
        set ok 0
        foreach expected $valid_nets {
            if {[regexp -nocase $expected $actual_net]} {
                set ok 1
                break
            }
        }
        if {!$ok} {
            lappend findings [finding \
                "$refdes: pin $pin_num ($signal_name) connected to '$actual_net' (unexpected)" \
                $refdes $actual_net $page_name]
        }
    }

    return $findings
}
