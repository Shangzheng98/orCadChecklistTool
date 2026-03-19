# OrCAD Capture TCL Extraction Scripts

## Setup

### Method 1: Manual execution
1. Open your design in OrCAD Capture
2. Open the TCL console (View > Command Window)
3. Run: `source /path/to/extract_design.tcl`
4. Run: `extract_and_export`

### Method 2: Auto-load
Copy the scripts to OrCAD's auto-load directory:
```
$CDS_ROOT/tools/capture/tclscripts/capAutoLoad/
```

### Method 3: Custom output path
```tcl
extract_and_export "C:/path/to/output.json"
```

## Output

The script generates a JSON file containing:
- Component list (RefDes, Value, Footprint, Part Number, properties, pins)
- Net list (name, connections, power classification)
- Unconnected pins
- Power nets
- Hierarchy (pages, hierarchical blocks)

This JSON file can then be uploaded to the OrCAD Checklist Tool web interface
or processed via the CLI: `orcad-check run output.json`
