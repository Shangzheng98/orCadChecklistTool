# ============================================================================
# OrCAD Checker - Embedded Tk GUI
# 在 OrCAD Capture 内弹出一个完整的工具窗口
# 包含: 检查面板 / AI 助手 / 脚本管理 三个 Tab
# ============================================================================

package require Tk
catch {wm withdraw .}

# ── Main Window ──────────────────────────────────────────────

proc orcad_checker_gui {} {
    # Prevent duplicate windows
    if {![catch {winfo exists .orcad_checker} result] && $result} {
        raise .orcad_checker
        return
    }

    toplevel .orcad_checker
    wm title .orcad_checker "OrCAD Checker Tool"
    wm geometry .orcad_checker 800x620
    wm minsize .orcad_checker 700 500

    # ── Notebook (Tabs) ──────────────────────────────────────
    ttk::notebook .orcad_checker.nb
    pack .orcad_checker.nb -fill both -expand 1 -padx 5 -pady 5

    # Tab 1: Design Check
    ttk::frame .orcad_checker.nb.check
    .orcad_checker.nb add .orcad_checker.nb.check -text "Design Check"
    build_check_tab .orcad_checker.nb.check

    # Tab 2: AI Assistant
    ttk::frame .orcad_checker.nb.ai
    .orcad_checker.nb add .orcad_checker.nb.ai -text "AI Assistant"
    build_ai_tab .orcad_checker.nb.ai

    # Tab 3: Script Manager
    ttk::frame .orcad_checker.nb.scripts
    .orcad_checker.nb add .orcad_checker.nb.scripts -text "Scripts"
    build_scripts_tab .orcad_checker.nb.scripts

    # Status bar
    ttk::label .orcad_checker.status -text "Ready" -relief sunken -anchor w
    pack .orcad_checker.status -fill x -side bottom -padx 5 -pady 2
}

proc set_status {msg} {
    if {[winfo exists .orcad_checker.status]} {
        .orcad_checker.status configure -text $msg
    }
}

# ============================================================================
# Tab 1: Design Check
# ============================================================================

proc build_check_tab {parent} {
    # ── Initialize checker variables ────────────────────────
    # P0
    set ::chk_duplicate_refdes 1
    set ::chk_footprint_validation 1
    set ::chk_decoupling_caps 1
    set ::chk_unused_pin_handling 1
    set ::chk_esd_protection 1
    # P1
    set ::chk_missing_attributes 1
    set ::chk_unconnected_pins 1
    set ::chk_power_net_naming 1
    set ::chk_single_pin_nets 1
    set ::chk_i2c_pullups 1
    set ::chk_crystal_load_caps 1
    set ::chk_reset_pin 1
    set ::chk_test_points 1
    set ::chk_power_voltage_label 1
    # P2
    set ::chk_net_naming 1
    set ::chk_impedance_matching 1
    set ::chk_standard_values 1
    set ::chk_thermal_pad 1
    set ::chk_connector_pinout 1

    # ── Horizontal paned window (left: results, right: checklist)
    ttk::panedwindow $parent.pw -orient horizontal
    pack $parent.pw -fill both -expand 1 -padx 5 -pady 5

    # ── Left panel: Results display ─────────────────────────
    ttk::frame $parent.pw.left
    $parent.pw add $parent.pw.left -weight 3

    ttk::label $parent.pw.left.title -text "Results" -font {Arial 11 bold}
    pack $parent.pw.left.title -anchor w -padx 5 -pady {5 2}

    ttk::frame $parent.pw.left.rf
    pack $parent.pw.left.rf -fill both -expand 1 -padx 5 -pady {0 5}

    text $parent.pw.left.rf.txt -wrap word \
        -yscrollcommand [list $parent.pw.left.rf.sb set] \
        -font {Consolas 10} -state disabled
    ttk::scrollbar $parent.pw.left.rf.sb -orient vertical \
        -command [list $parent.pw.left.rf.txt yview]

    pack $parent.pw.left.rf.sb -side right -fill y
    pack $parent.pw.left.rf.txt -fill both -expand 1

    # Tag colors for results (P0-P3 priority)
    $parent.pw.left.rf.txt tag configure pass -foreground "#27ae60"
    $parent.pw.left.rf.txt tag configure fail_p0 -foreground "#e74c3c" -font {Consolas 10 bold}
    $parent.pw.left.rf.txt tag configure fail_p1 -foreground "#e67e22" -font {Consolas 10 bold}
    $parent.pw.left.rf.txt tag configure fail_p2 -foreground "#3498db"
    $parent.pw.left.rf.txt tag configure fail_p3 -foreground "#95a5a6"
    $parent.pw.left.rf.txt tag configure header -font {Consolas 11 bold}
    $parent.pw.left.rf.txt tag configure finding -foreground "#555555" -lmargin1 30

    # ── Right panel: Checklist ──────────────────────────────
    ttk::frame $parent.pw.right
    $parent.pw add $parent.pw.right -weight 2

    ttk::label $parent.pw.right.title -text "Checklist" -font {Arial 11 bold}
    pack $parent.pw.right.title -anchor w -padx 5 -pady {5 2}

    # Select All / Deselect All at top
    ttk::frame $parent.pw.right.selbtns
    pack $parent.pw.right.selbtns -fill x -padx 5 -pady {0 5}

    ttk::button $parent.pw.right.selbtns.all -text "Select All" \
        -command gui_select_all
    ttk::button $parent.pw.right.selbtns.none -text "Deselect All" \
        -command gui_deselect_all
    pack $parent.pw.right.selbtns.all $parent.pw.right.selbtns.none \
        -side left -padx {0 5}

    # Scrollable checklist area (19 items need scroll)
    canvas $parent.pw.right.cvs -highlightthickness 0
    ttk::scrollbar $parent.pw.right.csb -orient vertical \
        -command [list $parent.pw.right.cvs yview]
    $parent.pw.right.cvs configure -yscrollcommand [list $parent.pw.right.csb set]

    pack $parent.pw.right.csb -side right -fill y
    pack $parent.pw.right.cvs -fill both -expand 1 -padx 5

    ttk::frame $parent.pw.right.cvs.checks
    $parent.pw.right.cvs create window 0 0 -anchor nw \
        -window $parent.pw.right.cvs.checks -tags checkwin

    set row 0
    foreach {var label} {
        chk_duplicate_refdes      "P0 Duplicate RefDes"
        chk_footprint_validation  "P0 Footprint Validation"
        chk_decoupling_caps       "P0 Decoupling Capacitors"
        chk_unused_pin_handling   "P0 Unused Pin Handling"
        chk_esd_protection        "P0 ESD Protection"
        chk_missing_attributes    "P1 Missing Attributes"
        chk_unconnected_pins      "P1 Unconnected Pins"
        chk_power_net_naming      "P1 Power Net Naming"
        chk_single_pin_nets       "P1 Single Pin Nets"
        chk_i2c_pullups           "P1 I2C Pull-ups"
        chk_crystal_load_caps     "P1 Crystal Load Caps"
        chk_reset_pin             "P1 Reset Pin Circuit"
        chk_test_points           "P1 Test Points"
        chk_power_voltage_label   "P1 Power Voltage Labels"
        chk_net_naming            "P2 Net Naming"
        chk_impedance_matching    "P2 Impedance Matching"
        chk_standard_values       "P2 Standard R/C Values"
        chk_thermal_pad           "P2 Thermal Pad Connection"
        chk_connector_pinout      "P2 Connector Pinout"
    } {
        ttk::checkbutton $parent.pw.right.cvs.checks.cb$row \
            -text $label -variable ::$var
        pack $parent.pw.right.cvs.checks.cb$row -anchor w -pady 1
        incr row
    }

    # Update scroll region when frame is resized
    bind $parent.pw.right.cvs.checks <Configure> \
        [list $parent.pw.right.cvs configure -scrollregion \
            [list 0 0 [list %w] [list %h]]]

    # Run and Upload buttons at bottom
    ttk::frame $parent.pw.right.actions
    pack $parent.pw.right.actions -fill x -padx 5 -pady {10 5} -side bottom

    ttk::button $parent.pw.right.actions.run -text "Run Selected" \
        -command [list gui_run_checks $parent]
    ttk::button $parent.pw.right.actions.upload -text "Upload to Server" \
        -command [list gui_upload_results] -state disabled

    pack $parent.pw.right.actions.run -fill x -pady {0 5}
    pack $parent.pw.right.actions.upload -fill x
}

proc _all_checker_vars {} {
    return {chk_duplicate_refdes chk_footprint_validation
        chk_decoupling_caps chk_unused_pin_handling chk_esd_protection
        chk_missing_attributes chk_unconnected_pins chk_power_net_naming
        chk_single_pin_nets chk_i2c_pullups chk_crystal_load_caps
        chk_reset_pin chk_test_points chk_power_voltage_label
        chk_net_naming chk_impedance_matching chk_standard_values
        chk_thermal_pad chk_connector_pinout}
}

proc gui_select_all {} {
    foreach var [_all_checker_vars] {
        set ::$var 1
    }
}

proc gui_deselect_all {} {
    foreach var [_all_checker_vars] {
        set ::$var 0
    }
}

proc gui_run_checks {parent} {
    set design [GetActiveDesign]
    if {$design eq ""} {
        tk_messageBox -parent .orcad_checker -icon error \
            -title "Error" -message "No active design. Please open a design first."
        return
    }

    set_status "Running checks..."
    update idletasks

    # Build checker list from checkboxes
    set checkers [list]
    set map {
        chk_duplicate_refdes      check_duplicate_refdes
        chk_footprint_validation  check_footprint_validation
        chk_decoupling_caps       check_decoupling_caps
        chk_unused_pin_handling   check_unused_pin_handling
        chk_esd_protection        check_esd_protection
        chk_missing_attributes    check_missing_attributes
        chk_unconnected_pins      check_unconnected_pins
        chk_power_net_naming      check_power_net_naming
        chk_single_pin_nets       check_single_pin_nets
        chk_i2c_pullups           check_i2c_pullups
        chk_crystal_load_caps     check_crystal_load_caps
        chk_reset_pin             check_reset_pin
        chk_test_points           check_test_points
        chk_power_voltage_label   check_power_voltage_label
        chk_net_naming            check_net_naming
        chk_impedance_matching    check_impedance_matching
        chk_standard_values       check_standard_values
        chk_thermal_pad           check_thermal_pad
        chk_connector_pinout      check_connector_pinout
    }
    foreach {var proc_name} $map {
        if {[set ::$var]} {
            lappend checkers $proc_name
        }
    }

    if {[llength $checkers] == 0} {
        tk_messageBox -parent .orcad_checker -icon warning \
            -title "Warning" -message "No checks selected."
        return
    }

    # Run checks (pass design to avoid double GetActiveDesign)
    run_all_checks $checkers $design

    # Display results in GUI
    set txt $parent.pw.left.rf.txt
    $txt configure -state normal
    $txt delete 1.0 end

    set design_name [GetDesignName $design]
    set p0 0; set p1 0; set p2 0; set p3 0; set passes 0

    foreach result $::check_results {
        set status [dict get $result status]
        set severity [dict get $result severity]
        if {$status eq "PASS"} {
            incr passes
        } else {
            switch $severity {
                "P0" { incr p0 }
                "P1" { incr p1 }
                "P2" { incr p2 }
                "P3" { incr p3 }
            }
        }
    }

    $txt insert end "Design: $design_name\n" header
    $txt insert end "Checks: [llength $::check_results] | PASS=$passes P0=$p0 P1=$p1 P2=$p2 P3=$p3\n" header
    $txt insert end [string repeat "-" 55] {}
    $txt insert end "\n"

    foreach result $::check_results {
        set rid  [dict get $result rule_id]
        set sev  [dict get $result severity]
        set stat [dict get $result status]
        set findings [dict get $result findings]

        if {$stat eq "PASS"} {
            $txt insert end "\[PASS\] \[$sev\] $rid\n" pass
        } else {
            set tag "fail_p1"
            switch $sev {
                "P0" { set tag "fail_p0" }
                "P1" { set tag "fail_p1" }
                "P2" { set tag "fail_p2" }
                "P3" { set tag "fail_p3" }
            }
            $txt insert end "\[FAIL\] \[$sev\] $rid\n" $tag
            foreach f $findings {
                $txt insert end "  - [dict get $f message]\n" finding
            }
        }
    }

    $txt configure -state disabled

    # Enable upload button
    $parent.pw.right.actions.upload configure -state normal

    set_status "Done. P0=$p0 P1=$p1 P2=$p2 P3=$p3 PASS=$passes"
}

proc gui_upload_results {} {
    set design [GetActiveDesign]
    if {$design eq ""} return
    set design_name [GetDesignName $design]

    if {[catch {upload_check_results $design_name} err]} {
        tk_messageBox -parent .orcad_checker -icon error \
            -title "Upload Failed" -message "Could not upload: $err"
    } else {
        set_status "Results uploaded to server."
        tk_messageBox -parent .orcad_checker -icon info \
            -title "Success" -message "Results uploaded to server."
    }
}

# ============================================================================
# Tab 2: AI Assistant
# ============================================================================

proc build_ai_tab {parent} {
    # AI Assistant tab - browser chat + fetch back to OrCAD
    ttk::frame $parent.main
    pack $parent.main -fill both -expand 1 -padx 20 -pady 10

    ttk::label $parent.main.title -text "AI Assistant" \
        -font {Arial 16 bold}
    pack $parent.main.title -pady {10 5}

    ttk::label $parent.main.desc -text \
        "1. Click 'Open AI Chat' to chat in browser\n2. Click 'Send to OrCAD' on generated code\n3. Click 'Fetch Script' below to load it" \
        -justify center
    pack $parent.main.desc -pady {0 15}

    # Open browser button
    ttk::button $parent.main.open -text "Open AI Chat in Browser" \
        -command gui_open_ai_chat
    pack $parent.main.open -pady 5 -ipadx 20 -ipady 6

    # Separator
    ttk::separator $parent.main.sep -orient horizontal
    pack $parent.main.sep -fill x -pady 15

    # Fetch section
    ttk::label $parent.main.fetch_label -text "Fetch AI-generated script:" \
        -font {Arial 11 bold}
    pack $parent.main.fetch_label -pady {0 5}

    ttk::frame $parent.main.btns
    pack $parent.main.btns -pady 5

    ttk::button $parent.main.btns.fetch -text "Fetch Script" \
        -command [list gui_ai_fetch $parent]
    ttk::button $parent.main.btns.exec -text "Execute in OrCAD" \
        -command gui_ai_exec_fetched -state disabled
    pack $parent.main.btns.fetch $parent.main.btns.exec -side left -padx 8 -ipadx 10 -ipady 4

    # Code preview
    ttk::labelframe $parent.main.preview -text "Script Preview"
    pack $parent.main.preview -fill both -expand 1 -pady {10 5}

    text $parent.main.preview.txt -wrap word -height 10 \
        -yscrollcommand [list $parent.main.preview.sb set] \
        -font {Consolas 10} -state disabled
    ttk::scrollbar $parent.main.preview.sb -orient vertical \
        -command [list $parent.main.preview.txt yview]
    pack $parent.main.preview.sb -side right -fill y
    pack $parent.main.preview.txt -fill both -expand 1

    # Status
    ttk::label $parent.main.status -text "" -foreground "#666666"
    pack $parent.main.status -pady {5 0}

    set ::ai_fetched_code ""
}

proc gui_open_ai_chat {} {
    set url "$::server_url/ai-chat"
    if {[catch {exec cmd /c start $url &} err]} {
        tk_messageBox -parent .orcad_checker -icon error \
            -title "Error" -message "Could not open browser: $err\n\nPlease open manually: $url"
    }
}

proc gui_ai_fetch {parent} {
    set status $parent.main.status
    set preview $parent.main.preview.txt
    set exec_btn $parent.main.btns.exec

    $status configure -text "Fetching..."
    update idletasks

    if {[catch {
        set resp [http_get "/api/v1/agent/clipboard"]
        set code [json_extract_field $resp "code"]
        set desc [json_extract_field $resp "description"]
    } err]} {
        $status configure -text "Error: $err"
        return
    }

    if {$code eq ""} {
        $status configure -text "No script available. Use 'Send to OrCAD' in browser first."
        $exec_btn configure -state disabled
        return
    }

    set ::ai_fetched_code $code
    $preview configure -state normal
    $preview delete 1.0 end
    $preview insert end $code
    $preview configure -state disabled
    $exec_btn configure -state normal
    $status configure -text "Script fetched. Review and click 'Execute in OrCAD'."
}

proc gui_ai_exec_fetched {} {
    if {$::ai_fetched_code eq ""} return

    set answer [tk_messageBox -parent .orcad_checker -icon question \
        -title "Execute Script" -type yesno \
        -message "Execute this TCL script in OrCAD?\n\nThis will run the code directly in Capture."]

    if {$answer eq "yes"} {
        set_status "Executing AI script..."
        if {[catch {uplevel #0 $::ai_fetched_code} err]} {
            tk_messageBox -parent .orcad_checker -icon error \
                -title "Execution Error" -message "Error: $err"
            set_status "Execution failed"
        } else {
            set_status "Script executed successfully"
        }
    }
}

# Legacy send function kept for compatibility
proc gui_ai_send {parent} {
    set msg ""
    if {[info exists ::ai_pending_msg]} { set msg $::ai_pending_msg; set ::ai_pending_msg "" }
    if {[string trim $msg] eq ""} return

    set txt $parent.chat.txt
    $txt configure -state normal
    $txt insert end "You: " user
    $txt insert end "$msg\n\n"
    $txt configure -state disabled
    $txt see end

    set_status "AI is thinking..."
    update idletasks

    if {[catch {
        set resp [agent_chat $::ai_session_id $msg]

        # Parse response - extract session_id, reply, extracted_code
        # Simple JSON field extraction
        set ::ai_session_id [json_extract_field $resp "session_id"]
        set reply [json_extract_field $resp "reply"]
        set code [json_extract_field $resp "extracted_code"]

        $txt configure -state normal
        $txt insert end "AI: " ai
        $txt insert end "$reply\n\n"
        $txt configure -state disabled
        $txt see end

        if {$code ne ""} {
            set ::ai_last_code $code
            $parent.actions.exec configure -state normal
            $parent.actions.save configure -state normal
        }

        set_status "Ready"
    } err]} {
        $txt configure -state normal
        $txt insert end "Error: $err\n\n" error_tag
        $txt configure -state disabled
        set_status "Error communicating with server"
    }
}

proc gui_ai_new {parent} {
    set ::ai_session_id ""
    set ::ai_last_code ""
    set txt $parent.chat.txt
    $txt configure -state normal
    $txt delete 1.0 end
    $txt configure -state disabled
    $parent.actions.exec configure -state disabled
    $parent.actions.save configure -state disabled
    set_status "New session started"
}

proc gui_ai_execute {parent} {
    if {$::ai_last_code eq ""} return

    set answer [tk_messageBox -parent .orcad_checker -icon question \
        -title "Execute Script" -type yesno \
        -message "Execute the generated TCL code in OrCAD?\n\nThis will run the code directly."]

    if {$answer eq "yes"} {
        set_status "Executing..."
        if {[catch {uplevel #0 $::ai_last_code} err]} {
            tk_messageBox -parent .orcad_checker -icon error \
                -title "Execution Error" -message "Error: $err"
            set_status "Execution failed"
        } else {
            set_status "Execution complete"
        }
    }
}

proc gui_ai_save {parent} {
    if {$::ai_last_code eq ""} return
    set name [string trim [$parent.actions.name get 1.0 end]]
    if {$name eq "" || $name eq "Script name..."} {
        tk_messageBox -parent .orcad_checker -icon warning \
            -title "Name Required" -message "Please enter a script name."
        return
    }

    if {[catch {
        agent_save_script $::ai_session_id $name $::ai_last_code
        tk_messageBox -parent .orcad_checker -icon info \
            -title "Saved" -message "Script '$name' saved to server."
        set_status "Script saved"
    } err]} {
        tk_messageBox -parent .orcad_checker -icon error \
            -title "Save Failed" -message "Error: $err"
    }
}

# ============================================================================
# Tab 3: Script Manager
# ============================================================================

proc build_scripts_tab {parent} {
    # ── Server scripts list ──────────────────────────────────
    ttk::labelframe $parent.server -text "Server Scripts"
    pack $parent.server -fill both -expand 1 -padx 5 -pady 5

    ttk::treeview $parent.server.tree -columns {name version category status author} \
        -show headings -height 8
    $parent.server.tree heading name -text "Name"
    $parent.server.tree heading version -text "Version"
    $parent.server.tree heading category -text "Category"
    $parent.server.tree heading status -text "Status"
    $parent.server.tree heading author -text "Author"

    $parent.server.tree column name -width 180
    $parent.server.tree column version -width 70
    $parent.server.tree column category -width 100
    $parent.server.tree column status -width 80
    $parent.server.tree column author -width 100

    ttk::scrollbar $parent.server.sb -orient vertical \
        -command [list $parent.server.tree yview]
    $parent.server.tree configure -yscrollcommand [list $parent.server.sb set]

    pack $parent.server.sb -side right -fill y
    pack $parent.server.tree -fill both -expand 1

    # ── Action buttons ───────────────────────────────────────
    ttk::frame $parent.btns
    pack $parent.btns -fill x -padx 5 -pady 5

    ttk::button $parent.btns.refresh -text "Refresh" \
        -command [list gui_scripts_refresh $parent]
    ttk::button $parent.btns.install -text "Install Selected" \
        -command [list gui_scripts_install $parent]
    ttk::button $parent.btns.check_update -text "Check OTA Updates" \
        -command [list gui_scripts_ota $parent]
    ttk::button $parent.btns.view -text "View Code" \
        -command [list gui_scripts_view $parent]

    pack $parent.btns.refresh $parent.btns.install \
        $parent.btns.check_update $parent.btns.view \
        -side left -padx 5

    # ── Code preview ─────────────────────────────────────────
    ttk::labelframe $parent.preview -text "Code Preview"
    pack $parent.preview -fill both -expand 1 -padx 5 -pady {0 5}

    text $parent.preview.txt -wrap none -height 8 \
        -yscrollcommand [list $parent.preview.sb set] \
        -font {Courier 10} -state disabled
    ttk::scrollbar $parent.preview.sb -orient vertical \
        -command [list $parent.preview.txt yview]

    pack $parent.preview.sb -side right -fill y
    pack $parent.preview.txt -fill both -expand 1
}

proc gui_scripts_refresh {parent} {
    set tree $parent.server.tree
    $tree delete [$tree children {}]

    set_status "Loading scripts from server..."
    update idletasks

    if {[catch {
        set resp [http_get "/api/v1/scripts"]
        # Parse JSON array of script objects
        set scripts [json_parse_script_list $resp]
        foreach s $scripts {
            $tree insert {} end -id [dict get $s id] \
                -values [list \
                    [dict get $s name] \
                    [dict get $s version] \
                    [dict get $s category] \
                    [dict get $s status] \
                    [dict get $s author]]
        }
        set_status "Loaded [llength $scripts] scripts"
    } err]} {
        set_status "Failed to load scripts: $err"
    }
}

proc gui_scripts_install {parent} {
    set tree $parent.server.tree
    set sel [$tree selection]
    if {$sel eq ""} {
        tk_messageBox -parent .orcad_checker -icon warning \
            -title "Select Script" -message "Please select a script to install."
        return
    }

    foreach script_id $sel {
        if {[catch {
            set resp [download_script $script_id]
            set_status "Installed: $script_id"
        } err]} {
            set_status "Install failed: $err"
        }
    }
}

proc gui_scripts_ota {parent} {
    set_status "Checking for updates..."
    update idletasks

    if {[catch {
        set resp [fetch_ota_manifest]
        set_status "OTA check complete"
        tk_messageBox -parent .orcad_checker -icon info \
            -title "OTA Updates" -message "Check complete. Refresh to see available scripts."
    } err]} {
        set_status "OTA check failed: $err"
    }
}

proc gui_scripts_view {parent} {
    set tree $parent.server.tree
    set sel [$tree selection]
    if {$sel eq ""} return

    set script_id [lindex $sel 0]
    set_status "Loading script code..."
    update idletasks

    if {[catch {
        set resp [http_get "/api/v1/scripts/$script_id"]
        set code [json_extract_field $resp "code"]

        set txt $parent.preview.txt
        $txt configure -state normal
        $txt delete 1.0 end
        $txt insert end $code
        $txt configure -state disabled
        set_status "Ready"
    } err]} {
        set_status "Failed to load: $err"
    }
}

# ============================================================================
# Minimal JSON parsing helpers (for server responses)
# ============================================================================

proc json_extract_field {json field} {
    # Extract a string value for a given key from JSON
    # Handles: "field":"value" and "field": "value"
    set pattern "\"${field}\"\\s*:\\s*\"((?:\[^\\\\\"\]|\\\\.)*)\""
    if {[regexp $pattern $json -> value]} {
        # Unescape
        set value [string map {\\\" \" \\\\ \\ \\n \n \\t \t} $value]
        return $value
    }
    return ""
}

proc json_parse_script_list {json} {
    # Parse array of script objects from server /api/v1/scripts response
    # Each object has: id, name, version, category, status, author
    set scripts [list]
    set fields {id name version category status author}

    # Split by object boundaries to find individual objects
    set items [regexp -all -inline {\{[^\}]+\}} $json]
    foreach item $items {
        set entry [dict create]
        foreach field $fields {
            dict set entry $field [json_extract_field $item $field]
        }
        # Only add if has an id
        if {[dict get $entry id] ne ""} {
            lappend scripts $entry
        }
    }
    return $scripts
}
