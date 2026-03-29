# Check: Footprint Validation
# 检查所有元件是否分配了封装

proc check_footprint_validation {design} {
    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue

            set footprint [GetPropValue $part "PCB Footprint"]
            if {$footprint eq ""} {
                set part_name [GetPropValue $part "Part Name"]
                lappend findings [finding \
                    "Component '$refdes' ($part_name) has no footprint" \
                    $refdes "" $page_name]
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "footprint_validation" $::CHECK_ERROR "PASS" [list]
    } else {
        check_result "footprint_validation" $::CHECK_ERROR "FAIL" $findings
    }
}
