# TCL & OrCAD DBO API Knowledge Base

This document complements `CLAUDE.md` with deeper TCL language guidance, extended DBO API
reference, common automation patterns, and embedded Tk GUI practices. It does NOT duplicate
what is already in `CLAUDE.md` -- read that first for the core calling conventions.

---

## 1. TCL Language Best Practices

### 1.1 Expression Bracing

Always surround expressions with `{braces}` in `expr`, `if`, `for`, and `while`. Braced
expressions are byte-compiled and avoid double-substitution bugs:

```tcl
# Good -- compiled, safe
if {$x > 0} { ... }
set y [expr {$a + $b}]

# Bad -- unbraced, re-parsed every call, injection risk
if $x>0 { ... }
set y [expr $a + $b]
```

### 1.2 String vs Numeric Comparison

Use `eq` / `ne` for string comparison and `==` / `!=` for numeric. This avoids
Tcl silently treating strings as numbers:

```tcl
if {$name eq "GND"}  { ... }   ;# string
if {$count == 0}     { ... }   ;# numeric
```

### 1.3 Safe Command Construction

Use `list` to build commands dynamically. It handles quoting automatically:

```tcl
# Safe -- list protects against special characters
set cmd [list after 100 myCallback $arg1 $arg2]
eval $cmd

# Dangerous -- manual quoting is error-prone
eval "after 100 myCallback $arg1 $arg2"
```

### 1.4 Variable Naming

- Use `snake_case` for local variables and procs.
- Use `CamelCase` only when mirroring DBO class names.
- Prefix namespace-private procs with `_` (e.g., `_dbo_status`).
- Use descriptive names: `page_name` not `pn`, `part_iter` not `pi`.

### 1.5 Boolean Clarity

Prefer `true`/`false` or `yes`/`no` over `1`/`0` for boolean variables when
the intent is not purely numeric:

```tcl
set is_power true
if {$is_power} { ... }
```

### 1.6 Proc Design

- Keep procs focused on a single responsibility.
- Return values rather than printing -- let the caller decide output.
- Use `upvar` sparingly; prefer return values.
- Document non-obvious parameters with a short comment above the proc.

### 1.7 Namespaces

Namespaces prevent global-scope collisions. For reusable libraries, wrap procs
in a namespace matching the package name:

```tcl
namespace eval ::mylib {
    namespace export public_proc

    proc public_proc {args} { ... }
    proc _private_helper {} { ... }
}
```

For OrCAD scripts that run in a shared interpreter, namespaces are strongly
recommended to avoid overwriting Capture's own procs.

#### Namespace Ensembles (Tcl 8.5+)

Ensembles turn a namespace into a sub-command style interface:

```tcl
namespace eval ::checker {
    namespace export run list clear
    namespace ensemble create

    proc run {design} { ... }
    proc list {} { ... }
    proc clear {} { ... }
}

# Usage: checker run $dsn
#        checker list
```

**Caveat:** OrCAD bundles Tcl 8.4 in older versions. Use `catch {namespace ensemble create}` or avoid ensembles if targeting pre-8.5.

### 1.8 Avoiding Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Unbalanced braces in comments | Never put `{` or `}` inside comments -- Tcl's parser counts them even in comments |
| Accidental glob in `string match` | Use `string equal` for exact match, `string match` only when you want glob |
| `info exists` on array element | `info exists arr(key)` works, but `info exists arr` returns true for the whole array |
| Modifying a list while iterating | Build a new list; don't `lreplace` mid-loop |

---

## 2. OrCAD Capture DBO API Reference (Extended)

> Core calling conventions (DboState, CString, iterators) are in `CLAUDE.md`.
> This section covers additional classes, discovery techniques, and lesser-known APIs.

### 2.1 API Discovery at Runtime

The most reliable way to find available commands is inside OrCAD's TCL console:

```tcl
# List all methods on a class
info commands DboPage_*
info commands DboPartInst_*
info commands DboNet_*
info commands DboFlatNet_*

# Find all classes that implement a method
info commands *_GetName*
info commands *_sGet*

# Get parameter info (intentionally call with wrong args)
DboPage_GetName
# -> Error: wrong # args: should be "DboPage_GetName self lName lStatus"
```

#### Journaling for API Exploration

Enable journaling to see what TCL commands OrCAD executes when you perform
GUI actions:

```tcl
SetOptionBool Journaling TRUE
SetOptionBool DisplayCommands TRUE
```

Then perform the action in the GUI (place a part, draw a wire, etc.) and
read the journal output. This is the primary way to discover undocumented
user-action commands.

### 2.2 Class Hierarchy

The DBO class hierarchy uses single inheritance. Subclasses inherit all
superclass methods. Key inheritance chains:

```
DboBaseObject
  +-- DboLibObject
        +-- DboLib
        |     +-- DboDesign (via DboLibToDboDesign cast)
        +-- DboSchematic
        +-- DboPage
        +-- DboPlacedInst
              +-- DboPartInst
        +-- DboNet
        +-- DboFlatNet
```

Because of inheritance, `DboBaseObject_GetEffectivePropStringValue` works on
any object in the hierarchy -- parts, nets, pages, etc.

### 2.3 Additional DBO Classes

| Class | Purpose |
|-------|---------|
| `DboSession` | Top-level session; holds active design |
| `DboDesign` | Design (.dsn) file; entry to schematics |
| `DboSchematic` | Root schematic; contains pages |
| `DboPage` | Single schematic page |
| `DboPartInst` | Placed component instance |
| `DboPlacedInst` | Base class for placed objects (parts, powers) |
| `DboPortInst` | Pin on a placed part |
| `DboNet` | Net on a single page |
| `DboFlatNet` | Cross-page flattened net |
| `DboPortOccurrence` | Pin in flattened (occurrence) domain |
| `DboInstOccurrence` | Part in flattened domain |
| `DboWire` | Wire segment |
| `DboTclHelper` | Utility: CString creation, type conversion |

### 2.4 Type Conversion Helpers

```tcl
# Create a CString for API calls that need one as input
set cstr [DboTclHelper_sMakeCString "my_property"]

# Create an integer wrapper
set intVal [DboTclHelper_sMakeInt 42]

# Read back a CString pointer
set tclStr [DboTclHelper_sGetConstCharPtr $cstr]

# Clean up allocated CStrings
DboTclHelper_sDeleteCString $cstr
```

### 2.5 Generic Property Access

The most flexible way to read any property on any DBO object:

```tcl
proc get_any_property {obj prop_name} {
    set st [DboState]
    set propCStr [DboTclHelper_sMakeCString $prop_name]
    set outCStr  [DboTclHelper_sMakeCString ""]
    if {![catch {
        DboBaseObject_GetEffectivePropStringValue $obj $propCStr $outCStr $st
    }]} {
        set result [DboTclHelper_sGetConstCharPtr $outCStr]
    } else {
        set result ""
    }
    DboTclHelper_sDeleteCString $propCStr
    DboTclHelper_sDeleteCString $outCStr
    return $result
}
```

### 2.6 Additional Iterators

Beyond the iterators listed in `CLAUDE.md`:

| What | Create | Advance |
|------|--------|---------|
| Wires on page | `DboPage_NewWiresIter` | `DboPageWiresIter_NextWire` |
| Sub-nets of FlatNet | `DboFlatNet_NewNetsIter` | `DboFlatNetNetsIter_NextNet` |
| Port instances on net | `DboNet_NewPortInstsIter` | `DboNetPortInstsIter_NextPortInst` |
| Properties on object | `DboBaseObject_NewPropertiesIter` | iterate with NextProperty |

### 2.7 Event Hooks (RegisterAction)

OrCAD provides event hooks for automatic script execution:

```tcl
# Register a callback for new schematic page creation
RegisterAction "_cdnOrOnNewSchematicPage" "capTrue" "" "::myns::on_new_page"

# Register for design open
RegisterAction "_cdnOrOnOpenDesign" "capTrue" "" "::myns::on_design_open"
```

- First arg: event name (prefixed with `_cdnOr`)
- Second arg: condition (`"capTrue"` = always)
- Third arg: reserved (empty string)
- Fourth arg: fully-qualified proc name to call

Multiple callbacks can be registered for the same event; they execute in
registration order.

### 2.8 Startup and Auto-Load

Scripts can be loaded automatically:

| Mechanism | Path |
|-----------|------|
| Init script | `$CDSROOT/tools/capture/tclscripts/capinit.tcl` |
| Auto-load dir | `$CDSROOT/tools/capture/tclscripts/capAutoLoad/` |
| Sample scripts | `$CDSROOT/tools/capture/tclscripts/` |

Place a `.tcl` file in `capAutoLoad/` and it will be sourced when Capture
starts. This is how plugins and extensions are deployed.

---

## 3. Common Automation Patterns

### 3.1 BOM Generation

```tcl
proc generate_bom {design outfile} {
    set st [DboState]
    set dsn $design
    catch {set dsn [DboLibToDboDesign $design]}

    set fd [open $outfile w]
    puts $fd "RefDes,Value,Footprint,Part Name,Library"

    set rootSch [DboDesign_GetRootSchematic $dsn $st]
    set pIter [DboSchematic_NewPagesIter $rootSch $st]
    set page [DboSchematicPagesIter_NextPage $pIter $st]

    while {$page ne "NULL"} {
        set partIter [DboPage_NewPartInstsIter $page $st]
        set part [DboPagePartInstsIter_NextPartInst $partIter $st]

        while {$part ne "NULL"} {
            set ref [DboTclHelper_sGetConstCharPtr \
                         [DboPartInst_sGetReference $part $st]]
            set val [DboTclHelper_sGetConstCharPtr \
                         [DboPartInst_sGetPartValue $part $st]]
            set fp  [DboTclHelper_sGetConstCharPtr \
                         [DboPlacedInst_sGetPCBFootprint $part $st]]
            set lib [DboTclHelper_sGetConstCharPtr \
                         [DboPlacedInst_sGetSourceLibName $part $st]]
            set pname [DboTclHelper_sGetConstCharPtr \
                           [DboLibObject_sGetName $part $st]]

            puts $fd "$ref,$val,$fp,$pname,$lib"

            set part [DboPagePartInstsIter_NextPartInst $partIter $st]
        }

        set page [DboSchematicPagesIter_NextPage $pIter $st]
    }

    close $fd
    puts "BOM written to $outfile"
}
```

### 3.2 Net Connectivity Validation

```tcl
proc find_floating_nets {design} {
    set st [DboState]
    set dsn $design
    catch {set dsn [DboLibToDboDesign $design]}

    set floating [list]
    set nIter [DboDesign_NewFlatNetsIter $dsn $st]
    set net [DboDesignFlatNetsIter_NextFlatNet $nIter $st]

    while {$net ne "NULL"} {
        set name [DboTclHelper_sGetConstCharPtr [DboFlatNet_sGetName $net $st]]

        # Count port occurrences (pin connections)
        set pin_count 0
        set poIter [DboFlatNet_NewPortOccurrencesIter $net $st]
        set po [DboFlatNetPortOccurrencesIter_NextPortOccurrence $poIter $st]
        while {$po ne "NULL"} {
            incr pin_count
            set po [DboFlatNetPortOccurrencesIter_NextPortOccurrence $poIter $st]
        }

        if {$pin_count <= 1} {
            lappend floating [list name $name pins $pin_count]
        }

        set net [DboDesignFlatNetsIter_NextFlatNet $nIter $st]
    }

    return $floating
}
```

### 3.3 Design Rule Check Pattern

The project uses a consistent pattern for checkers (see `tcl/checkers/`):

```tcl
proc check_<rule_name> {design} {
    set findings [list]

    # 1. Iterate over design objects
    foreach page [GetPages $design] {
        foreach part [GetPartInsts $page] {
            # 2. Apply rule logic
            if {<violation_detected>} {
                lappend findings [finding \
                    "Description of violation" \
                    $refdes "" [GetName $page]]
            }
        }
    }

    # 3. Report result
    if {[llength $findings] == 0} {
        check_result "<rule_name>" $::CHECK_ERROR "PASS" [list]
    } else {
        check_result "<rule_name>" $::CHECK_ERROR "FAIL" $findings
    }
}
```

Key conventions:
- Checker proc name: `check_<rule_name>`
- Takes `$design` as sole argument
- Uses `finding` helper for structured messages
- Uses `check_result` to record pass/fail with severity

### 3.4 Property Bulk Export

```tcl
proc export_all_properties {design outfile} {
    set st [DboState]
    set fd [open $outfile w]

    foreach page [GetPages $design] {
        foreach part [GetPartInsts $page] {
            set ref [GetPropValue $part "Reference"]
            puts $fd "=== $ref ==="

            # Use the generic property iterator
            foreach prop_name {Reference Value "PCB Footprint" "Source Library"
                               Manufacturer Description Tolerance Datasheet
                               "Part Number"} {
                set val [GetPropValue $part $prop_name]
                if {$val ne ""} {
                    puts $fd "  $prop_name = $val"
                }
            }
        }
    }

    close $fd
}
```

### 3.5 Cross-Reference Report

```tcl
proc net_to_pins_report {design} {
    set nets [GetFlatNets $design]
    foreach net $nets {
        set name [GetNetName $net]
        set pins [GetNetPins $net]
        puts "Net '$name': [llength $pins] connection(s)"
        foreach pin $pins {
            set ref [GetPinRefDes $pin]
            puts "  -> $ref"
        }
    }
}
```

---

## 4. GUI Development in Embedded Tk

### 4.1 OrCAD-Specific Tk Constraints

OrCAD's embedded Tcl includes Tk, but with restrictions:

- **Root window `.`**: `package require Tk` creates it. Always hide with
  `catch {wm withdraw .}` -- OrCAD manages its own root window.
- **`toplevel` for tool windows**: Create `.orcad_checker` or similar named
  windows; never reuse `.`.
- **No blocking dialogs in callbacks**: `tk_messageBox` is OK for short
  confirmations; never block the event loop for long operations.
- **`update idletasks`**: Call periodically during long operations to keep the
  GUI responsive. Do NOT call `update` (processes all events, can cause re-entrancy).

### 4.2 Window Lifecycle Pattern

```tcl
proc my_tool_gui {} {
    # 1. Prevent duplicates
    if {![catch {winfo exists .my_tool} result] && $result} {
        raise .my_tool
        return
    }

    # 2. Create toplevel
    toplevel .my_tool
    wm title .my_tool "My Tool"
    wm geometry .my_tool 600x400
    wm minsize .my_tool 400 300

    # 3. Build widgets
    # ...

    # 4. Handle window close
    wm protocol .my_tool WM_DELETE_WINDOW {
        destroy .my_tool
    }
}
```

### 4.3 ttk Widget Recommendations

Prefer `ttk::` widgets over classic Tk widgets for a native look:

| Use | Instead of |
|-----|-----------|
| `ttk::button` | `button` |
| `ttk::label` | `label` |
| `ttk::frame` | `frame` |
| `ttk::notebook` | manual tab switching |
| `ttk::treeview` | `listbox` for tabular data |
| `ttk::entry` | `entry` |

### 4.4 Layout Strategy

Use `pack` for simple vertical/horizontal stacking and `grid` for forms:

```tcl
# pack -- good for toolbar-style layouts
pack $btn1 $btn2 $btn3 -side left -padx 5

# grid -- good for label+entry forms
grid $label -row 0 -column 0 -sticky e
grid $entry -row 0 -column 1 -sticky ew
grid columnconfigure $parent 1 -weight 1
```

Avoid mixing `pack` and `grid` in the same parent frame.

### 4.5 Text Widget with Tags

For colored, styled output (as used in the check results display):

```tcl
text $w.txt -state disabled -font {Consolas 10}

# Define tags
$w.txt tag configure pass       -foreground "#27ae60"
$w.txt tag configure fail_error -foreground "#e74c3c" -font {Consolas 10 bold}
$w.txt tag configure header     -font {Consolas 11 bold}

# Write with tags
$w.txt configure -state normal
$w.txt insert end "PASS\n" pass
$w.txt insert end "ERROR\n" fail_error
$w.txt configure -state disabled
```

### 4.6 Progress Feedback

For long-running operations, use a status bar and `update idletasks`:

```tcl
proc long_operation {status_label} {
    set total [llength $items]
    set i 0
    foreach item $items {
        # Process item...
        incr i
        $status_label configure -text "Processing $i / $total..."
        update idletasks
    }
    $status_label configure -text "Done."
}
```

### 4.7 Separating GUI from Logic

Keep business logic (checkers, data extraction) in separate files from
the GUI. The GUI should:
- Call logic procs and receive return values
- Format results for display
- Never contain DBO API calls directly

This separation enables:
- Running checks from the console without a GUI
- Testing logic independently
- Reusing logic in different interfaces (CLI, HTTP upload, GUI)

---

## 5. Error Handling Patterns

### 5.1 The `catch` Idiom

`catch` is the primary error handling mechanism. It returns 0 on success, 1
on error:

```tcl
if {[catch {some_risky_call $arg} result]} {
    # Error: $result contains the error message
    puts "Error: $result"
} else {
    # Success: $result contains the return value
    puts "Got: $result"
}
```

### 5.2 Try/Finally (Tcl 8.6+)

If your Tcl version supports it:

```tcl
try {
    set fd [open $filename r]
    set data [read $fd]
} on error {msg opts} {
    puts "Failed to read: $msg"
} finally {
    catch {close $fd}
}
```

**Note:** OrCAD may ship Tcl 8.4 or 8.5. Use `catch` as the safe default.

### 5.3 DBO API Error Handling

Wrap every DBO call in `catch` because the SWIG bindings throw on invalid
objects or wrong arguments:

```tcl
# Pattern: attempt, check, fallback
if {![catch {set cstr [DboPartInst_sGetReference $part $st]}]} {
    set refdes [DboTclHelper_sGetConstCharPtr $cstr]
} else {
    set refdes ""
}
```

### 5.4 Graceful Degradation

When a feature might not be available (e.g., TLS, specific DBO method):

```tcl
# Try optional package
if {[catch {package require tls}] == 0} {
    http::register https 443 [list ::tls::socket -autoservername true]
} else {
    puts "WARNING: TLS not available, HTTPS disabled"
}
```

### 5.5 User-Facing Error Messages

Never expose raw Tcl stack traces to users. Catch errors and present
context-appropriate messages:

```tcl
if {[catch {run_all_checks $checkers} err]} {
    tk_messageBox -icon error -title "Check Failed" \
        -message "Could not complete design checks.\n\nDetails: $err"
}
```

### 5.6 Defensive Iterator Pattern

Iterators can fail at creation or during iteration. Always guard both:

```tcl
proc safe_iterate_parts {page} {
    set st [_dbo_status]
    set parts [list]

    if {[catch {set iter [DboPage_NewPartInstsIter $page $st]}]} {
        return $parts  ;# empty list, not an error
    }

    if {![catch {set part [DboPagePartInstsIter_NextPartInst $iter $st]}]} {
        while {$part ne "NULL"} {
            lappend parts $part
            if {[catch {set part [DboPagePartInstsIter_NextPartInst $iter $st]}]} {
                break
            }
        }
    }

    return $parts
}
```

---

## 6. Testing Approaches

### 6.1 tcltest Framework

Tcl ships with `tcltest` for unit testing:

```tcl
package require tcltest
namespace import ::tcltest::*

test json_escape-1.0 "Escape double quotes" -body {
    json_escape {He said "hello"}
} -result {"He said \"hello\""}

test json_escape-1.1 "Escape backslash" -body {
    json_escape {C:\path}
} -result {"C:\\path"}

cleanupTests
```

### 6.2 Testing Outside OrCAD

DBO API calls only work inside OrCAD's interpreter. For testing logic that
depends on DBO data, use a two-layer approach:

1. **Adapter layer** (`lib/orcad_api.tcl`): thin wrapper around DBO calls.
2. **Logic layer** (checkers, extractors): operates on data returned by the adapter.

For testing, mock the adapter procs:

```tcl
# Mock for testing outside OrCAD
proc GetPages {design} {
    return [list "mock_page_1" "mock_page_2"]
}

proc GetPartInsts {page} {
    return [list "mock_part_1"]
}

proc GetPropValue {part prop} {
    switch $prop {
        "Reference" { return "R1" }
        "Value"     { return "10k" }
        default     { return "" }
    }
}

# Now run the checker -- it calls the mocked procs
source checkers/duplicate_refdes.tcl
check_duplicate_refdes "mock_design"
```

### 6.3 Validation Inside OrCAD

Use the diagnostic probe pattern:

```tcl
proc orcad_api_probe {} {
    # Verify API access works
    # Print summary of design objects found
    # Exercise each iterator and property getter
    # Report any failures
}
```

Run `orcad_api_probe` after loading scripts to verify the environment.

### 6.4 Smoke Testing Checklist

Before deploying a new checker or script update:

- [ ] Run `orcad_api_probe` -- all items report OK
- [ ] Run `run_all_checks` on a known-good design -- all PASS
- [ ] Run `run_all_checks` on a design with known issues -- correct FAILs
- [ ] Open GUI, run checks via buttons -- results display correctly
- [ ] Upload results to server -- no HTTP errors
- [ ] Test with design closed (should show "No active design" error)

---

## 7. Useful Resources and Links

### Official Cadence Resources

- **OrCAD Capture Tcl/Tk Extensions PDF** (primary API reference):
  `$CDSROOT/tools/capture/tclscripts/OrCAD_Capture_TclTk_Extensions.pdf`
  Also available at: [EMA-EDA hosted copy](https://www.ema-eda.com/wp-content/uploads/files/resources/files/OrCAD_Capture_TclTk_Extensions.pdf)

- **FlowCAD TCL-TK Commands Application Note**:
  [FlowCAD_AN_Capture_TCL-TK_Commands.pdf](https://www.flowcad.de/AN/FlowCAD_AN_Capture_TCL-TK_Commands.pdf)

- **OrCAD X TCL Scripting Blog**:
  [OrCAD X Tcl Scripts: Automate to Accelerate Turnarounds](https://resources.pcb.cadence.com/blog/2024-orcad-x-tcl-scripts-automate-to-accelerate-turnarounds)

- **Cadence Community Forums**:
  [OrCAD Capture TCL scripting thread](https://community.cadence.com/cadence_technology_forums/pcb-design/f/pcb-design/15614/orcad-capture-tcl-scripting)

### Community Examples

- **z-Wind/OrcadTcl** (GitHub): [MIT-licensed OrCAD TCL examples](https://github.com/z-Wind/OrcadTcl)
  Includes: Custom_Launch.tcl, AddNetsToParts.tcl, replaceGlobalPower.tcl, showProperty.tcl

- **Digital Spelunk 42**: [Cadence OrCAD notes](https://dsp42.blogspot.com/2014/11/notes-cadence-orcad.html)
  Covers journaling, init files, auto-load directories

### TCL Language Resources

- **Tcler's Wiki -- Best Practices**: [wiki.tcl-lang.org/page/Best+Practices](https://wiki.tcl-lang.org/page/Best+Practices)
- **Tcler's Wiki -- Namespaces**: [wiki.tcl-lang.org/page/namespace](https://wiki.tcl-lang.org/page/namespace)
- **Tcler's Wiki -- EDA**: [wiki.tcl-lang.org/page/EDA](https://wiki.tcl-lang.org/page/EDA)
- **tcltest manual**: [tcltest on Tcler's Wiki](https://wiki.tcl-lang.org/page/tcltest)
- **Tcl Tutorial -- Packages and Namespaces**: [tcl-lang.org tutorial](https://www.tcl-lang.org/man/tcltutorial/html/Tcl31.html)

### Key Installation Paths

| What | Path |
|------|------|
| Init script | `$CDSROOT/tools/capture/tclscripts/capinit.tcl` |
| Auto-load directory | `$CDSROOT/tools/capture/tclscripts/capAutoLoad/` |
| Sample scripts | `$CDSROOT/tools/capture/tclscripts/` |
| API reference PDF | `$CDSROOT/tools/capture/tclscripts/OrCAD_Capture_TclTk_Extensions.pdf` |
