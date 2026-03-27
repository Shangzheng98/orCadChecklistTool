# ============================================================================
# OrCAD Checker Tool - Main Entry Point
# ============================================================================
#
# Usage in OrCAD Capture TCL Console:
#
#   source "C:/path/to/orcad_checker.tcl"
#
# This will:
#   1. Load check engine + all checkers
#   2. Load HTTP client (for server communication)
#   3. Load Tk GUI
#   4. Open the checker window
#
# Commands available after loading:
#   orcad_checker_gui          - Open the GUI window
#   run_all_checks             - Run all checks (text output)
#   run_single_check <name>    - Run one check
#   upload_check_results <name> - Upload results to server
#
# ============================================================================

set _orcad_checker_root [file dirname [info script]]

# Server URL (override before sourcing if needed)
if {![info exists ::server_url]} {
    set ::server_url "http://localhost:8000"
}

puts "Loading OrCAD Checker Tool..."

# Load check engine
source [file join $_orcad_checker_root engine check_engine.tcl]

# Load all checkers
source [file join $_orcad_checker_root checkers load_all.tcl]

# Load HTTP client
source [file join $_orcad_checker_root engine http_client.tcl]

# Load GUI
source [file join $_orcad_checker_root gui main_window.tcl]

puts "OrCAD Checker Tool loaded."
puts "  - 7 checkers available"
puts "  - Server: $::server_url"
puts ""
puts "Commands:"
puts "  orcad_checker_gui    - Open GUI"
puts "  run_all_checks       - Run all checks (console)"
puts ""

# Auto-open GUI
orcad_checker_gui
