# Extract component data from OrCAD Capture design
# Returns a list of component dicts

proc extract_components {design} {
    set components [list]

    # Iterate through all schematic pages
    set pages [GetPages $design]
    foreach page $pages {
        set page_name [GetName $page]

        # Iterate through all part instances on this page
        set parts [GetPartInsts $page]
        foreach part $parts {
            set refdes [GetPropValue $part "Reference"]
            set value [GetPropValue $part "Value"]
            set footprint [GetPropValue $part "PCB Footprint"]
            set part_name [GetPropValue $part "Part Name"]
            set part_number [GetPropValue $part "Part Number"]
            set library [GetPropValue $part "Source Library"]

            # Get all properties
            set props [dict create]
            set prop_names [list "Manufacturer" "Description" "Tolerance" "Datasheet"]
            foreach pname $prop_names {
                set pval [GetPropValue $part $pname]
                if {$pval ne ""} {
                    dict set props $pname $pval
                }
            }

            # Get pins
            set pins [list]
            set pin_list [GetPins $part]
            foreach pin $pin_list {
                set pin_number [GetPinNumber $pin]
                set pin_name [GetPinName $pin]
                set pin_type [GetPinType $pin]
                set net_name [GetPinNet $pin]

                lappend pins [dict create \
                    number $pin_number \
                    name $pin_name \
                    type $pin_type \
                    net $net_name \
                ]
            }

            lappend components [dict create \
                refdes $refdes \
                part_name $part_name \
                value $value \
                footprint $footprint \
                part_number $part_number \
                library $library \
                page $page_name \
                properties $props \
                pins $pins \
            ]
        }
    }

    return $components
}
