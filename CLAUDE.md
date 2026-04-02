# OrCAD Checklist Tool

## Project Structure

- `tcl/` — OrCAD Capture TCL scripts (run inside OrCAD's TCL console)
  - `lib/orcad_api.tcl` — DBO API adapter layer (all other scripts call this)
  - `lib/checker_utils.tcl` — shared checker utilities (component detection, net map, caching)
  - `engine/check_engine.tcl` — check engine with P0-P3 priority levels
  - `engine/http_client.tcl` — HTTP client for server communication
  - `checkers/` — 19 individual design rule checkers
  - `gui/main_window.tcl` — Tk GUI (embedded in OrCAD)
- `tcl/orcad_checker.tcl` — main entry point, sources everything
- `src/orcad_checker/` — Python backend (FastAPI)
- `docs/tcl_knowledge_base.md` — TCL scripting knowledge base

## OrCAD DBO TCL API Conventions

OrCAD Capture's TCL API uses SWIG-generated bindings. These rules were discovered through testing on OrCAD 25.1 and are **not documented by Cadence**.

### Calling Style

All methods use `ClassName_MethodName $object $args...` (NOT `$object Method`):

```tcl
set rootSch [DboDesign_GetRootSchematic $dsn $lStatus]
```

### DboState Required

Almost all methods require a `DboState` object as the last argument:

```tcl
set lStatus [DboState]
set rootSch [DboDesign_GetRootSchematic $dsn $lStatus]
puts [DboState_Code $lStatus]  ;# 0 = success
```

### CString Handling

`sGet` methods return CString pointers (not Tcl strings). Convert with:

```tcl
set cstr [DboPartInst_sGetReference $part $lStatus]
set refdes [DboTclHelper_sGetConstCharPtr $cstr]
```

### Return Types to Watch

- **sGet methods** → return CString pointer, convert with `DboTclHelper_sGetConstCharPtr`
- **sGetPinType** → returns integer enum (0=INPUT, 1=OUTPUT, 2=BIDIRECTIONAL, 3=POWER, 4=PASSIVE, 5=OPEN_COLLECTOR, 6=OPEN_EMITTER, 7=HIZ), NOT CString
- **GetIsPower** → returns boolean integer
- **GetName with out-parameter** → `DboPage_GetName $page lName $st` sets `lName` as Tcl string directly

### Iterator Pattern

```tcl
set iter [DboSchematic_NewPagesIter $rootSch $lStatus]
set page [DboSchematicPagesIter_NextPage $iter $lStatus]
while {$page ne "NULL"} {
    # process $page
    set page [DboSchematicPagesIter_NextPage $iter $lStatus]
}
```

### Design Entry Point

```tcl
set design [DboSession_GetActiveDesign $::DboSession_s_pDboSession]
set dsn [DboLibToDboDesign $design]  ;# cast needed for DboDesign methods
```

### Key Property Getters

| Property | API Call |
|----------|----------|
| Reference | `DboPartInst_sGetReference $part $st` |
| Value | `DboPartInst_sGetPartValue $part $st` |
| PCB Footprint | `DboPlacedInst_sGetPCBFootprint $part $st` |
| Source Library | `DboPlacedInst_sGetSourceLibName $part $st` |
| Page Name | `DboPage_GetName $page lName $st` (out-parameter) |
| Pin Type | `DboPortInst_sGetPinType $pin $st` (returns integer enum) |

### Common Iterators

| What | Create | Advance |
|------|--------|---------|
| Pages | `DboSchematic_NewPagesIter` | `DboSchematicPagesIter_NextPage` |
| Parts | `DboPage_NewPartInstsIter` | `DboPagePartInstsIter_NextPartInst` |
| Pins | `DboPartInst_NewPinsIter` | `DboPartInstPinsIter_NextPin` |
| Flat Nets | `DboDesign_NewFlatNetsIter` | `DboDesignFlatNetsIter_NextFlatNet` |

### Power Net Detection

Use `DboFlatNet_GetIsPower` to check if a net is a power net. Fallback to name pattern matching:

```tcl
regexp -nocase {^(VCC|VDD|AVCC|AVDD|VBAT|VIN|VOUT|V\d|GND|AGND|DGND|VSS|AVSS|0$)} $net_name
```

## SWIG Crash Zones — DO NOT CALL

These APIs cause OrCAD to **segfault/crash** (no error, instant exit). There is no way to `catch` them.

### FlatNet Pin Iteration

**NEVER** iterate pins through FlatNet objects:

```tcl
# CRASHES — do not use
DboFlatNet_NewPortOccurrencesIter $net $st
DboFlatNetPortOccurrencesIter_NextPortOccurrence $iter $st

# CRASHES — do not use  
DboFlatNet_NewNetsIter → DboNet_NewPortInstsIter → DboPortInst_GetOwner

# CRASHES — do not use
DboInstOccurrence_sGetReferenceDesignator $portOccurrence $st
DboPortOccurrence_FindInstance $portOccurrence $st
```

### Safe Alternative: Build Net Map from Page/Part/Pin

Instead of iterating FlatNet pins, build the net-component map by iterating pages → parts → pins:

```tcl
set net_map [dict create]
foreach page [GetPages $design] {
    foreach part [GetPartInsts $page] {
        set refdes [GetPropValue $part "Reference"]
        foreach pin [GetPins $part] {
            set net_name [GetPinNet $pin]
            if {$net_name eq ""} continue
            set entry [list $refdes [GetPinName $pin] [GetPinNumber $pin]]
            dict lappend net_map $net_name $entry
        }
    }
}
```

This is implemented in `checker_utils.tcl` as `build_net_components_map` with caching.

### Net Map Data Format

`build_net_components_map` returns a dict where:
- Key: net name (string)
- Value: list of `{refdes pin_name pin_number}` **lists** (NOT dicts)

Access with `lindex`, NOT `dict get`:

```tcl
foreach comp [dict get $net_map $net_name] {
    set refdes  [lindex $comp 0]
    set pinname [lindex $comp 1]
    set pinnum  [lindex $comp 2]
}
```

## TCL Gotchas

### Braces in Comments

Tcl counts `{` and `}` in comments when matching proc bodies. This is the **#1 source of mysterious parse errors**.

```tcl
# BAD — this breaks proc parsing:
# Split by },{ to find objects

# GOOD — rephrase to avoid braces:
# Split by object boundaries to find objects
```

### Variable vs Array Confusion

`$var($other)` is Tcl array access. Use `${var}(${other})` for string interpolation:

```tcl
# BAD — Tcl tries to read array element:
set msg "pin $pin_name($pin_num)"

# GOOD — explicit variable boundaries:
set msg "pin ${pin_name}(${pin_num})"
```

### Package Availability

- **`package require tls`** — not available in OrCAD's embedded Tcl. Load optionally with `catch`.
- **`package require Tk`** — creates a root `.` window. Hide with `catch {wm withdraw .}`.
- **Tk IME support** — Chinese input broken in OrCAD's embedded Tk. Use browser-based UI for text input.

### Tk Lifecycle

Once Tk is destroyed (`destroy .`), `package require Tk` cannot reinitialize it. Must restart OrCAD.

### DboState Reuse

Create one global `DboState` and reuse it. Do NOT create a new one per call:

```tcl
set ::_dbo_status ""
proc _dbo_status {} {
    if {$::_dbo_status eq ""} { set ::_dbo_status [DboState] }
    return $::_dbo_status
}
```

## Checker Development Guide

### Priority Levels

| Level | Meaning | Color |
|-------|---------|-------|
| P0 | Critical — must fix | Red |
| P1 | Serious — strongly recommended | Orange |
| P2 | Moderate — consider fixing | Blue |
| P3 | Info — suggestion only | Gray |

### Checker Template

```tcl
proc check_xxx {design} {
    set findings [list]
    foreach page [GetPages $design] {
        set page_name [GetName $page]
        foreach part [GetPartInsts $page] {
            set refdes [GetPropValue $part "Reference"]
            # ... check logic ...
            if {$problem} {
                lappend findings [finding "description" $refdes $net $page_name]
            }
        }
    }
    if {[llength $findings] == 0} {
        check_result "xxx" $::CHECK_P1 "PASS" [list]
    } else {
        check_result "xxx" $::CHECK_P1 "FAIL" $findings
    }
}
```

### Using Net Map in Checkers

```tcl
set net_map [build_net_components_map $design]
# Check if a net has a capacitor:
net_has_component_type $net_name $net_map {^C[0-9]}
# Check if a net has a resistor:
net_has_component_type $net_name $net_map {^R[0-9]}
```

### Component Type Detection (from checker_utils.tcl)

- `is_ic $part` — pin count > 4 and not passive/connector prefix
- `is_capacitor $refdes` — refdes starts with C
- `is_resistor $refdes` — refdes starts with R
- `is_connector $refdes` — refdes starts with J, P, or CN
- `is_test_point $refdes` — refdes starts with TP

### Performance: Caching

`build_net_components_map` and `collect_power_net_names` cache their results globally. Call `clear_checker_cache` (done automatically by `clear_results`) before re-running checks.

### Integration Checklist for New Checkers

1. Create `tcl/checkers/check_xxx.tcl`
2. Add `source` line in `tcl/checkers/load_all.tcl`
3. Add to default list in `tcl/engine/check_engine.tcl`
4. Add checkbox variable `set ::chk_xxx 1` in `build_check_tab`
5. Add to checkbox `foreach` list in `build_check_tab`
6. Add to `_all_checker_vars` proc
7. Add mapping in `gui_run_checks` map
