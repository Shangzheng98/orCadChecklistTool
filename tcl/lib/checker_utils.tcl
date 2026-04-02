# ============================================================================
# Shared Checker Utilities
# Helper procs for design rule checkers
# ============================================================================

# Caches
set ::_net_comp_cache [list]
set ::_power_nets_cache [list]

# ── Component Type Detection ────────────────────────────────

proc is_ic {part} {
    set refdes [GetPropValue $part "Reference"]
    set prefix [get_refdes_prefix $refdes]

    # Passives and connectors are not ICs
    set non_ic_prefixes {C R L D J P CN TP F FB}
    foreach p $non_ic_prefixes {
        if {[string equal -nocase $prefix $p]} {
            return 0
        }
    }

    # Must have more than 4 pins
    set pins [GetPins $part]
    if {[llength $pins] <= 4} {
        return 0
    }

    return 1
}

proc is_capacitor {refdes} {
    return [regexp -nocase {^C[0-9]} $refdes]
}

proc is_resistor {refdes} {
    return [regexp -nocase {^R[0-9]} $refdes]
}

proc is_connector {refdes} {
    return [regexp -nocase {^(J|P|CN)[0-9]} $refdes]
}

proc is_test_point {refdes} {
    return [regexp -nocase {^TP[0-9]} $refdes]
}

proc get_refdes_prefix {refdes} {
    if {[regexp {^([A-Za-z]+)} $refdes -> prefix]} {
        return $prefix
    }
    return ""
}

# ── Power Net Collection ────────────────────────────────────

proc collect_power_net_names {design} {
    if {[llength $::_power_nets_cache] > 0} {
        return $::_power_nets_cache
    }

    set power_nets [list]

    # Method 1: Use FlatNet IsPower flag
    foreach net [GetFlatNets $design] {
        set st [_dbo_status]
        if {![catch {set is_pwr [DboFlatNet_GetIsPower $net $st]}]} {
            if {$is_pwr} {
                set nname [GetNetName $net]
                if {$nname ne "" && [lsearch -exact $power_nets $nname] < 0} {
                    lappend power_nets $nname
                }
            }
        }
    }

    # Method 2: If method 1 found nothing, match by net name pattern
    if {[llength $power_nets] == 0} {
        foreach net [GetFlatNets $design] {
            set nname [GetNetName $net]
            if {[regexp -nocase {^(VCC|VDD|AVCC|AVDD|VBAT|VIN|VOUT|V\d|GND|AGND|DGND|VSS|AVSS|0$)} $nname]} {
                if {[lsearch -exact $power_nets $nname] < 0} {
                    lappend power_nets $nname
                }
            }
        }
    }

    set ::_power_nets_cache $power_nets
    return $power_nets
}

# ── Net-Components Map ──────────────────────────────────────

proc build_net_components_map {design} {
    if {[llength $::_net_comp_cache] > 0} {
        return $::_net_comp_cache
    }

    # Build map by iterating pages/parts/pins (safe, no FlatNet pin access)
    set net_map [dict create]
    foreach page [GetPages $design] {
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            if {$refdes eq ""} continue
            foreach pin [GetPins $part] {
                set net_name [GetPinNet $pin]
                if {$net_name eq ""} continue
                set pin_name [GetPinName $pin]
                set pin_num [GetPinNumber $pin]
                set entry [list $refdes $pin_name $pin_num]
                if {[dict exists $net_map $net_name]} {
                    dict lappend net_map $net_name $entry
                } else {
                    dict set net_map $net_name [list $entry]
                }
            }
        }
    }

    set ::_net_comp_cache $net_map
    return $net_map
}

proc net_has_component_type {net_name net_map prefix_pattern} {
    if {![dict exists $net_map $net_name]} {
        return 0
    }
    foreach comp [dict get $net_map $net_name] {
        set refdes [lindex $comp 0]
        if {[regexp -nocase $prefix_pattern $refdes]} {
            return 1
        }
    }
    return 0
}

# ── Cache Management ────────────────────────────────────────

proc clear_checker_cache {} {
    set ::_net_comp_cache [list]
    set ::_power_nets_cache [list]
}

puts "Checker utilities loaded."
