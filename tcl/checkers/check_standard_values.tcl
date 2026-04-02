# Check: Standard Component Values (E24 Series)
# 检查电阻和电容是否使用E24标准值

proc check_standard_values {design} {
    # E24 series mantissa values
    set e24 {1.0 1.1 1.2 1.3 1.5 1.6 1.8 2.0 2.2 2.4 2.7 3.0
             3.3 3.6 3.9 4.3 4.7 5.1 5.6 6.2 6.8 7.5 8.2 9.1}

    set findings [list]

    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue

            # Only check resistors and capacitors
            if {![is_resistor $refdes] && ![is_capacitor $refdes]} continue

            set value [GetPropValue $part "Value"]
            if {$value eq ""} continue

            # Skip special values
            set val_upper [string toupper $value]
            if {$val_upper eq "DNP" || $val_upper eq "0" || $val_upper eq "0R"} continue

            # Parse the numeric value with suffix
            set numeric [parse_component_value $value]
            if {$numeric < 0} continue

            # Normalize to mantissa in range 1.0 to 10.0
            if {$numeric == 0} continue
            set mantissa $numeric
            while {$mantissa >= 10.0} {
                set mantissa [expr {$mantissa / 10.0}]
            }
            while {$mantissa < 1.0} {
                set mantissa [expr {$mantissa * 10.0}]
            }

            # Check against E24 values with 5% tolerance
            set matched 0
            foreach e $e24 {
                set ratio [expr {$mantissa / $e}]
                if {$ratio >= 0.95 && $ratio <= 1.05} {
                    set matched 1
                    break
                }
            }

            if {!$matched} {
                lappend findings [finding \
                    "$refdes value '$value' is not a standard E24 value" \
                    $refdes "" $page_name]
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "standard_values" $::CHECK_P2 "PASS" [list]
    } else {
        check_result "standard_values" $::CHECK_P2 "FAIL" $findings
    }
}

# Parse component value string to numeric (ohms or farads base)
# Handles suffixes: k, M, G, m, u, n, p
# Returns -1 if unparseable
proc parse_component_value {val} {
    # Remove trailing units like ohm, F, R
    set val [string trim $val]
    regsub -nocase {[oO]hm[s]?$|[fF]$} $val "" val
    set val [string trim $val]

    # Handle inline multiplier notation like 4k7 or 2R2
    if {[regexp -nocase {^(\d+)([kKmMuUnNpPrR])(\d+)$} $val -> whole suffix frac]} {
        set numeric [expr {double("${whole}.${frac}")}]
        set multiplier [value_suffix_multiplier $suffix]
        return [expr {$numeric * $multiplier}]
    }

    # Handle standard notation like 100k, 4.7u, 10n
    if {[regexp -nocase {^([0-9]*\.?[0-9]+)\s*([kKmMuUnNpPgG]?)$} $val -> numeric suffix]} {
        if {$numeric eq ""} {return -1}
        set multiplier [value_suffix_multiplier $suffix]
        return [expr {double($numeric) * $multiplier}]
    }

    return -1
}

# Return multiplier for a value suffix character
proc value_suffix_multiplier {suffix} {
    switch -- $suffix {
        "G" - "g" { return 1e9 }
        "M"       { return 1e6 }
        "k" - "K" { return 1e3 }
        "R" - "r" - "" { return 1.0 }
        "m"       { return 1e-3 }
        "u" - "U" { return 1e-6 }
        "n" - "N" { return 1e-9 }
        "p" - "P" { return 1e-12 }
        default   { return 1.0 }
    }
}
