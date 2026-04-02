# ============================================================================
# OrCAD Capture DBO API Adapter
# Maps simplified API calls to real OrCAD DBO TCL SWIG bindings
#
# Calling conventions discovered:
#   - All methods require a DboState parameter: $lStatus
#   - sGet methods return CString ptr, convert with DboTclHelper_sGetConstCharPtr
#   - Iterators: NewXxxIter $obj $lStatus -> XxxIter_NextXxx $iter $lStatus
#   - Iterator returns "NULL" when exhausted
#   - DboSession_GetActiveDesign returns DboDesign ptr
#   - DboLibToDboDesign casts DboLib to DboDesign
# ============================================================================

# Global DboState object, created once
set ::_dbo_status ""

proc _dbo_status {} {
    if {$::_dbo_status eq ""} {
        set ::_dbo_status [DboState]
    }
    return $::_dbo_status
}

# Helper: CString ptr -> Tcl string
proc _cstr {cstring_ptr} {
    if {$cstring_ptr eq "" || $cstring_ptr eq "NULL"} {
        return ""
    }
    return [DboTclHelper_sGetConstCharPtr $cstring_ptr]
}

# ── Diagnostic Probe ────────────────────────────────────────

proc orcad_api_probe {} {
    set st [_dbo_status]
    puts "=== OrCAD DBO API Probe ==="

    # Get design
    set design [GetActiveDesign]
    if {$design eq ""} {
        puts "\[FAIL\] No active design"
        return
    }
    puts "\[OK\] Active design: $design"
    puts "\[OK\] Design name: [GetDesignName $design]"

    # Get pages
    set pages [GetPages $design]
    puts "\[OK\] Pages: [llength $pages]"

    set total_parts 0
    foreach page $pages {
        set pname [GetName $page]
        set parts [GetPartInsts $page]
        set nparts [llength $parts]
        incr total_parts $nparts
        puts "  Page '$pname': $nparts parts"

        # Show first 3 parts
        set shown 0
        foreach part $parts {
            if {$shown >= 3} break
            set ref [GetPropValue $part "Reference"]
            set val [GetPropValue $part "Value"]
            set fp [GetPropValue $part "PCB Footprint"]
            puts "    $ref = $val ($fp)"
            incr shown
        }
        if {$nparts > 3} {
            puts "    ... and [expr {$nparts - 3}] more"
        }
    }

    # Get flat nets
    set nets [GetFlatNets $design]
    puts "\[OK\] Flat nets: [llength $nets]"
    set shown 0
    foreach net $nets {
        if {$shown >= 5} break
        puts "  Net: [GetNetName $net]"
        incr shown
    }
    if {[llength $nets] > 5} {
        puts "  ... and [expr {[llength $nets] - 5}] more"
    }

    puts ""
    puts "=== Probe Complete: $total_parts parts, [llength $nets] nets ==="
}

# ============================================================================
# Design-level functions
# ============================================================================

proc GetActiveDesign {} {
    set st [_dbo_status]

    if {![info exists ::DboSession_s_pDboSession]} {
        puts "ERROR: Not in OrCAD Capture TCL console"
        return ""
    }

    if {![catch {set design [DboSession_GetActiveDesign $::DboSession_s_pDboSession]}]} {
        if {$design ne "" && $design ne "NULL"} {
            return $design
        }
    }

    puts "ERROR: No active design. Please open a design first."
    return ""
}

proc GetDesignName {design} {
    set st [_dbo_status]
    if {![catch {set cstr [DboLib_sGetName $design $st]}]} {
        set name [_cstr $cstr]
        if {$name ne ""} { return $name }
    }
    if {![catch {DboLib_GetName $design lName $st}]} {
        return $lName
    }
    return "Unknown"
}

proc GetDesignFileName {design} {
    set st [_dbo_status]
    if {![catch {set cstr [DboLib_GetPath $design $st]}]} {
        return [_cstr $cstr]
    }
    return ""
}

# ============================================================================
# Page functions
# ============================================================================

proc GetPages {design} {
    set st [_dbo_status]
    set pages [list]

    # Cast to DboDesign if needed
    set dsn $design
    catch {set dsn [DboLibToDboDesign $design]}

    # Get root schematic
    if {[catch {set rootSch [DboDesign_GetRootSchematic $dsn $st]} err]} {
        puts "ERROR: GetRootSchematic failed: $err"
        return $pages
    }
    if {$rootSch eq "NULL"} { return $pages }

    # Iterate pages
    if {[catch {set pIter [DboSchematic_NewPagesIter $rootSch $st]} err]} {
        puts "ERROR: NewPagesIter failed: $err"
        return $pages
    }

    if {![catch {set page [DboSchematicPagesIter_NextPage $pIter $st]}]} {
        while {$page ne "NULL"} {
            lappend pages $page
            if {[catch {set page [DboSchematicPagesIter_NextPage $pIter $st]}]} {
                break
            }
        }
    }

    return $pages
}

proc GetName {page} {
    set st [_dbo_status]
    if {![catch {DboPage_GetName $page lName $st}]} {
        return $lName
    }
    if {![catch {set cstr [DboPage_sGetName $page $st]}]} {
        return [_cstr $cstr]
    }
    return ""
}

proc GetPageTitle {page} {
    return [GetName $page]
}

# ============================================================================
# Part Instance functions
# ============================================================================

proc GetPartInsts {page} {
    set st [_dbo_status]
    set parts [list]

    if {[catch {set partIter [DboPage_NewPartInstsIter $page $st]}]} {
        return $parts
    }

    if {![catch {set part [DboPagePartInstsIter_NextPartInst $partIter $st]}]} {
        while {$part ne "NULL"} {
            lappend parts $part
            if {[catch {set part [DboPagePartInstsIter_NextPartInst $partIter $st]}]} {
                break
            }
        }
    }

    return $parts
}

proc GetPropValue {part prop_name} {
    set st [_dbo_status]

    switch -- $prop_name {
        "Reference" {
            if {![catch {set cstr [DboPartInst_sGetReference $part $st]}]} {
                return [_cstr $cstr]
            }
        }
        "Value" {
            if {![catch {set cstr [DboPartInst_sGetPartValue $part $st]}]} {
                return [_cstr $cstr]
            }
        }
        "PCB Footprint" {
            if {![catch {set cstr [DboPlacedInst_sGetPCBFootprint $part $st]}]} {
                return [_cstr $cstr]
            }
        }
        "Part Name" {
            if {![catch {set cstr [DboLibObject_sGetName $part $st]}]} {
                return [_cstr $cstr]
            }
            if {![catch {set cstr [DboBaseObject_GetName $part $st]}]} {
                return [_cstr $cstr]
            }
        }
        "Part Number" {
            # Try generic property getter
        }
        "Source Library" {
            if {![catch {set cstr [DboPlacedInst_sGetSourceLibName $part $st]}]} {
                return [_cstr $cstr]
            }
        }
    }

    # Generic: try GetEffectivePropStringValue with CString argument
    if {![catch {
        set propCStr [DboTclHelper_sMakeCString $prop_name]
        set outCStr [DboTclHelper_sMakeCString ""]
        DboBaseObject_GetEffectivePropStringValue $part $propCStr $outCStr $st
        set result [_cstr $outCStr]
        DboTclHelper_sDeleteCString $propCStr
        DboTclHelper_sDeleteCString $outCStr
    }]} {
        if {[info exists result] && $result ne ""} {
            return $result
        }
    }

    return ""
}

# ============================================================================
# Pin functions
# ============================================================================

proc GetPins {part} {
    set st [_dbo_status]
    set pins [list]

    if {[catch {set pinIter [DboPartInst_NewPinsIter $part $st]}]} {
        return $pins
    }

    if {![catch {set pin [DboPartInstPinsIter_NextPin $pinIter $st]}]} {
        while {$pin ne "NULL"} {
            lappend pins $pin
            if {[catch {set pin [DboPartInstPinsIter_NextPin $pinIter $st]}]} {
                break
            }
        }
    }

    return $pins
}

proc GetPinNumber {pin} {
    set st [_dbo_status]
    if {![catch {set cstr [DboPortInst_sGetPinNumber $pin $st]}]} {
        return [_cstr $cstr]
    }
    return ""
}

proc GetPinName {pin} {
    set st [_dbo_status]
    if {![catch {set cstr [DboPortInst_sGetPinName $pin $st]}]} {
        return [_cstr $cstr]
    }
    if {![catch {set cstr [DboSymbolPin_sGetPinName $pin $st]}]} {
        return [_cstr $cstr]
    }
    return ""
}

proc GetPinType {pin} {
    set st [_dbo_status]
    # sGetPinType returns an integer enum, not CString
    # 0=INPUT, 1=OUTPUT, 2=BIDIRECTIONAL, 3=POWER, 4=PASSIVE, 5=OPEN_COLLECTOR, 6=OPEN_EMITTER, 7=HIZ
    if {![catch {set ptype [DboPortInst_sGetPinType $pin $st]}]} {
        switch -- $ptype {
            0 { return "INPUT" }
            1 { return "OUTPUT" }
            2 { return "BIDIRECTIONAL" }
            3 { return "POWER" }
            4 { return "PASSIVE" }
            5 { return "OPEN_COLLECTOR" }
            6 { return "OPEN_EMITTER" }
            7 { return "HIZ" }
            default { return $ptype }
        }
    }
    return ""
}

proc GetPinNet {pin} {
    set st [_dbo_status]

    # Method 1: sGetNetName
    if {![catch {set cstr [DboPortInst_sGetNetName $pin $st]}]} {
        set name [_cstr $cstr]
        if {$name ne ""} { return $name }
    }

    # Method 2: GetNet then get name
    if {![catch {set net [DboPortInst_GetNet $pin $st]}]} {
        if {$net ne "" && $net ne "NULL"} {
            if {![catch {set cstr [DboNet_sGetNetName $net $st]}]} {
                return [_cstr $cstr]
            }
            if {![catch {set cstr [DboNet_sGetName $net $st]}]} {
                return [_cstr $cstr]
            }
        }
    }

    return ""
}

# ============================================================================
# Power Pin functions
# ============================================================================

proc GetPowerPins {page} {
    set st [_dbo_status]
    set power_pins [list]

    # Iterate all parts, check if power symbol
    foreach part [GetPartInsts $page] {
        set is_power 0
        if {![catch {set cstr [DboPartInst_sGetIsPrimitive $part $st]}]} {
            # Primitive parts with specific reference patterns are often power
        }
        # Check via power pins visible flag
        if {![catch {set cstr [DboPartInst_sGetPowerPinsAreVisible $part $st]}]} {
            set is_power 1
        }

        if {$is_power} {
            foreach pin [GetPins $part] {
                lappend power_pins $pin
            }
        }
    }

    # If no power-specific detection worked, check net names
    # Power nets typically start with VCC, VDD, GND, etc.
    return $power_pins
}

# ============================================================================
# Net functions
# ============================================================================

proc GetFlatNets {design} {
    set st [_dbo_status]
    set nets [list]

    set dsn $design
    catch {set dsn [DboLibToDboDesign $design]}

    if {[catch {set nIter [DboDesign_NewFlatNetsIter $dsn $st]}]} {
        return $nets
    }

    if {![catch {set flatNet [DboDesignFlatNetsIter_NextFlatNet $nIter $st]}]} {
        while {$flatNet ne "NULL"} {
            lappend nets $flatNet
            if {[catch {set flatNet [DboDesignFlatNetsIter_NextFlatNet $nIter $st]}]} {
                break
            }
        }
    }

    return $nets
}

proc GetNetName {net} {
    set st [_dbo_status]
    # DboFlatNet
    if {![catch {set cstr [DboFlatNet_sGetName $net $st]}]} {
        return [_cstr $cstr]
    }
    # DboNet
    if {![catch {set cstr [DboNet_sGetNetName $net $st]}]} {
        return [_cstr $cstr]
    }
    if {![catch {set cstr [DboNet_sGetName $net $st]}]} {
        return [_cstr $cstr]
    }
    return ""
}

proc GetNetPins {net} {
    # NOTE: FlatNet pin iteration crashes OrCAD SWIG bindings.
    # Use build_net_components_map from checker_utils.tcl instead,
    # which safely builds the net-to-components map from page/part/pin iteration.
    # This proc is kept for compatibility but returns empty list.
    return [list]
}

proc GetPinRefDes {pin} {
    # NOTE: Calling DBO methods on FlatNet pin objects crashes OrCAD.
    # Use build_net_components_map from checker_utils.tcl instead.
    return ""
}

# ============================================================================
puts "OrCAD DBO API adapter loaded."
