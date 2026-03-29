# Check: Missing Attributes (Footprint, Value, Part Number)
# 直接读取 OrCAD 元件属性，无需导出

proc check_missing_attributes {design} {
    # Configurable required attributes
    set required_attrs [list "PCB Footprint" "Value" "Part Number"]

    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue

            set missing [list]
            foreach attr $required_attrs {
                set val [GetPropValue $part $attr]
                if {$val eq ""} {
                    lappend missing $attr
                }
            }

            if {[llength $missing] > 0} {
                lappend findings [finding \
                    "Component '$refdes' missing: [join $missing {, }]" \
                    $refdes "" $page_name]
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "missing_attributes" $::CHECK_WARNING "PASS" [list]
    } else {
        check_result "missing_attributes" $::CHECK_WARNING "FAIL" $findings
    }
}
