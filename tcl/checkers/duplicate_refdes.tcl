# Check: Duplicate Reference Designators
# 直接在 OrCAD 内部遍历所有页面，查找重复 RefDes

proc check_duplicate_refdes {design} {
    array set refdes_pages {}

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue

            if {[info exists refdes_pages($refdes)]} {
                lappend refdes_pages($refdes) $page_name
            } else {
                set refdes_pages($refdes) [list $page_name]
            }
        }
    }

    set findings [list]
    foreach refdes [array names refdes_pages] {
        set pages $refdes_pages($refdes)
        if {[llength $pages] > 1} {
            lappend findings [finding \
                "Duplicate RefDes '$refdes' on pages: [join $pages {, }]" \
                $refdes "" [lindex $pages 0]]
        }
    }

    if {[llength $findings] == 0} {
        check_result "duplicate_refdes" $::CHECK_ERROR "PASS" [list]
    } else {
        check_result "duplicate_refdes" $::CHECK_ERROR "FAIL" $findings
    }
}
