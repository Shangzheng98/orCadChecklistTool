# OrCAD Capture Design Data Extraction Script
# Usage: Run from OrCAD Capture's TCL console or capAutoLoad directory
#
# This script extracts design data and exports it as JSON for the
# OrCAD Checklist Tool to analyze.

# Load helper libraries
set script_dir [file dirname [info script]]
source [file join $script_dir lib components.tcl]
source [file join $script_dir lib nets.tcl]
source [file join $script_dir lib power.tcl]
source [file join $script_dir export_json.tcl]

proc extract_and_export {{output_path ""}} {
    # Get active design
    set design [GetActiveDesign]
    if {$design eq ""} {
        puts "ERROR: No active design found. Please open a design first."
        return
    }

    set design_name [GetDesignName $design]
    set source_file [GetDesignFileName $design]

    # Default output path
    if {$output_path eq ""} {
        set output_path [file join [file dirname $source_file] "${design_name}_export.json"]
    }

    puts "Extracting design data from: $design_name"

    # Extract power nets first (needed for net classification)
    puts "  Extracting power nets..."
    set power_nets [extract_power_nets $design]

    # Extract components
    puts "  Extracting components..."
    set components [extract_components $design]

    # Extract nets
    puts "  Extracting nets..."
    set net_data [extract_nets $design $power_nets]
    set nets [dict get $net_data nets]
    set unconnected_pins [dict get $net_data unconnected_pins]

    # Extract hierarchy info
    puts "  Extracting hierarchy..."
    set pages_json [list]
    set page_num 0
    set pages [GetPages $design]
    foreach page $pages {
        incr page_num
        set pname [GetName $page]
        set ptitle [GetPageTitle $page]
        lappend pages_json "\{\"name\": [to_json_string $pname], \"title\": [to_json_string $ptitle], \"page_number\": $page_num\}"
    }

    # Get timestamp
    set timestamp [clock format [clock seconds] -format "%Y-%m-%dT%H:%M:%SZ" -gmt true]

    # Build final JSON
    set json_parts [list]
    lappend json_parts "\"schema_version\": \"1.0.0\""
    lappend json_parts "\"design_name\": [to_json_string $design_name]"
    lappend json_parts "\"export_timestamp\": [to_json_string $timestamp]"
    lappend json_parts "\"source_file\": [to_json_string $source_file]"
    lappend json_parts "\"components\": [to_json_list $components component_to_json]"
    lappend json_parts "\"nets\": [to_json_list $nets net_to_json]"
    lappend json_parts "\"unconnected_pins\": [to_json_list $unconnected_pins unconnected_pin_to_json]"
    lappend json_parts "\"power_nets\": [to_json_string_list $power_nets]"
    lappend json_parts "\"hierarchy\": \{\"top_level\": [to_json_string $design_name], \"pages\": \[[join $pages_json ,]\], \"hierarchical_blocks\": \[\]\}"

    set json "\{[join $json_parts ,]\}"

    # Write to file
    write_json_file $output_path $json

    puts "Export complete: $output_path"
    puts "Components: [llength $components]"
    puts "Nets: [llength $nets]"
    puts "Power nets: [llength $power_nets]"

    return $output_path
}

# Auto-run if executed directly
if {[info exists ::argv0] && $::argv0 eq [info script]} {
    extract_and_export
}
