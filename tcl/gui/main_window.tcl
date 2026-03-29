# ============================================================================
# OrCAD Checker - Embedded Tk GUI
# 在 OrCAD Capture 内弹出一个完整的工具窗口
# 包含: 检查面板 / AI 助手 / 脚本管理 三个 Tab
# ============================================================================

package require Tk

# ── Main Window ──────────────────────────────────────────────

proc orcad_checker_gui {} {
    # Prevent duplicate windows
    if {[winfo exists .orcad_checker]} {
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
    # ── Checker selection ────────────────────────────────────
    ttk::labelframe $parent.sel -text "Select Checks"
    pack $parent.sel -fill x -padx 5 -pady 5

    set ::chk_duplicate_refdes 1
    set ::chk_missing_attributes 1
    set ::chk_unconnected_pins 1
    set ::chk_footprint_validation 1
    set ::chk_power_net_naming 1
    set ::chk_net_naming 1
    set ::chk_single_pin_nets 1

    set row 0
    foreach {var label} {
        chk_duplicate_refdes    "Duplicate RefDes (ERROR)"
        chk_missing_attributes  "Missing Attributes (WARNING)"
        chk_unconnected_pins    "Unconnected Pins (WARNING)"
        chk_footprint_validation "Footprint Validation (ERROR)"
        chk_power_net_naming    "Power Net Naming (WARNING)"
        chk_net_naming          "Net Naming (INFO)"
        chk_single_pin_nets     "Single Pin Nets (WARNING)"
    } {
        ttk::checkbutton $parent.sel.cb$row -text $label -variable ::$var
        grid $parent.sel.cb$row -row [expr {$row / 2}] -column [expr {$row % 2}] \
            -sticky w -padx 10 -pady 2
        incr row
    }

    # ── Buttons ──────────────────────────────────────────────
    ttk::frame $parent.btn
    pack $parent.btn -fill x -padx 5 -pady 5

    ttk::button $parent.btn.run -text "Run Checks" -command [list gui_run_checks $parent]
    ttk::button $parent.btn.all -text "Select All" -command gui_select_all
    ttk::button $parent.btn.none -text "Deselect All" -command gui_deselect_all
    ttk::button $parent.btn.upload -text "Upload to Server" \
        -command [list gui_upload_results] -state disabled

    pack $parent.btn.run $parent.btn.all $parent.btn.none $parent.btn.upload \
        -side left -padx 5

    # ── Results display ──────────────────────────────────────
    ttk::labelframe $parent.results -text "Results"
    pack $parent.results -fill both -expand 1 -padx 5 -pady 5

    text $parent.results.txt -wrap word -height 15 \
        -yscrollcommand [list $parent.results.sb set] \
        -font {Consolas 10} -state disabled
    ttk::scrollbar $parent.results.sb -orient vertical \
        -command [list $parent.results.txt yview]

    pack $parent.results.sb -side right -fill y
    pack $parent.results.txt -fill both -expand 1

    # Tag colors for results
    $parent.results.txt tag configure pass -foreground "#27ae60"
    $parent.results.txt tag configure fail_error -foreground "#e74c3c" -font {Consolas 10 bold}
    $parent.results.txt tag configure fail_warning -foreground "#f39c12"
    $parent.results.txt tag configure fail_info -foreground "#3498db"
    $parent.results.txt tag configure header -font {Consolas 11 bold}
    $parent.results.txt tag configure finding -foreground "#555555" -lmargin1 30
}

proc gui_select_all {} {
    foreach var {chk_duplicate_refdes chk_missing_attributes chk_unconnected_pins
                 chk_footprint_validation chk_power_net_naming chk_net_naming
                 chk_single_pin_nets} {
        set ::$var 1
    }
}

proc gui_deselect_all {} {
    foreach var {chk_duplicate_refdes chk_missing_attributes chk_unconnected_pins
                 chk_footprint_validation chk_power_net_naming chk_net_naming
                 chk_single_pin_nets} {
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
        chk_duplicate_refdes    check_duplicate_refdes
        chk_missing_attributes  check_missing_attributes
        chk_unconnected_pins    check_unconnected_pins
        chk_footprint_validation check_footprint_validation
        chk_power_net_naming    check_power_net_naming
        chk_net_naming          check_net_naming
        chk_single_pin_nets     check_single_pin_nets
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

    # Run checks
    run_all_checks $checkers

    # Display results in GUI
    set txt $parent.results.txt
    $txt configure -state normal
    $txt delete 1.0 end

    set design_name [GetDesignName $design]
    set errors 0; set warnings 0; set passes 0

    foreach result $::check_results {
        set status [dict get $result status]
        if {$status eq "PASS"} { incr passes } else {
            if {[dict get $result severity] eq "ERROR"} { incr errors } else { incr warnings }
        }
    }

    $txt insert end "Design: $design_name\n" header
    $txt insert end "Checks: [llength $::check_results] | Pass: $passes | Error: $errors | Warning: $warnings\n" header
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
            set tag "fail_warning"
            if {$sev eq "ERROR"} { set tag "fail_error" }
            if {$sev eq "INFO"}  { set tag "fail_info" }
            $txt insert end "\[FAIL\] \[$sev\] $rid\n" $tag
            foreach f $findings {
                $txt insert end "  - [dict get $f message]\n" finding
            }
        }
    }

    $txt configure -state disabled

    # Enable upload button
    $parent.btn.upload configure -state normal

    set_status "Done. $errors error(s), $warnings warning(s)."
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
    set ::ai_session_id ""

    # Chat display
    ttk::labelframe $parent.chat -text "Conversation"
    pack $parent.chat -fill both -expand 1 -padx 5 -pady 5

    text $parent.chat.txt -wrap word -height 18 \
        -yscrollcommand [list $parent.chat.sb set] \
        -font {Consolas 10} -state disabled
    ttk::scrollbar $parent.chat.sb -orient vertical \
        -command [list $parent.chat.txt yview]

    pack $parent.chat.sb -side right -fill y
    pack $parent.chat.txt -fill both -expand 1

    $parent.chat.txt tag configure user -foreground "#2c3e50" -font {Consolas 10 bold}
    $parent.chat.txt tag configure ai -foreground "#2980b9"
    $parent.chat.txt tag configure code -background "#f5f5f5" -font {Courier 10}
    $parent.chat.txt tag configure error_tag -foreground "#e74c3c"

    # Input area
    ttk::frame $parent.input
    pack $parent.input -fill x -padx 5 -pady 5

    ttk::entry $parent.input.entry -font {Consolas 10}
    ttk::button $parent.input.send -text "Send" -command [list gui_ai_send $parent]
    ttk::button $parent.input.new -text "New Session" -command [list gui_ai_new $parent]

    pack $parent.input.entry -side left -fill x -expand 1 -padx {0 5}
    pack $parent.input.send -side left -padx {0 5}
    pack $parent.input.new -side left

    bind $parent.input.entry <Return> [list gui_ai_send $parent]

    # Action buttons for generated code
    ttk::frame $parent.actions
    pack $parent.actions -fill x -padx 5 -pady {0 5}

    ttk::button $parent.actions.exec -text "Execute in OrCAD" \
        -command [list gui_ai_execute $parent] -state disabled
    ttk::button $parent.actions.save -text "Save to Server" \
        -command [list gui_ai_save $parent] -state disabled
    ttk::entry $parent.actions.name -width 25
    $parent.actions.name insert 0 "Script name..."

    pack $parent.actions.exec $parent.actions.save -side left -padx 5
    pack $parent.actions.name -side left -padx 5 -fill x -expand 1

    set ::ai_last_code ""
}

proc gui_ai_send {parent} {
    set entry $parent.input.entry
    set msg [string trim [$entry get]]
    if {$msg eq ""} return
    $entry delete 0 end

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
    set name [string trim [$parent.actions.name get]]
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

    # Split by },{ to find individual objects
    set items [regexp -all -inline {\{[^}]+\}} $json]
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
