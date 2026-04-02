# ============================================================================
# HTTP Client for OrCAD TCL → Server communication
# Uses TCL's built-in http package
# ============================================================================

package require http

# TLS support: only load if available (not bundled in OrCAD's Tcl)
set _has_tls [catch {package require tls}]
if {$_has_tls == 0} {
    http::register https 443 [list ::tls::socket -autoservername true]
}
unset _has_tls

# Default server URL
if {![info exists ::server_url]} {
    set ::server_url "http://localhost:8000"
}

# ── Core HTTP helpers ────────────────────────────────────────

proc http_get {path} {
    set url "${::server_url}${path}"
    set token [http::geturl $url -timeout 15000]
    set body [http::data $token]
    set code [http::ncode $token]
    http::cleanup $token

    if {$code != 200} {
        error "HTTP GET $path failed with code $code"
    }
    return $body
}

proc http_post {path body {content_type "application/json"}} {
    set url "${::server_url}${path}"
    set token [http::geturl $url \
        -method POST \
        -type $content_type \
        -query $body \
        -timeout 30000]
    set resp [http::data $token]
    set code [http::ncode $token]
    http::cleanup $token

    if {$code >= 400} {
        error "HTTP POST $path failed with code $code: $resp"
    }
    return $resp
}

# ── JSON helpers (minimal parser) ────────────────────────────

proc json_escape {str} {
    set str [string map {\\ \\\\ \" \\\" \n \\n \t \\t \r \\r} $str]
    return "\"$str\""
}

proc json_list_of_strings {lst} {
    set items [list]
    foreach item $lst {
        lappend items [json_escape $item]
    }
    return "\[[join $items ,]\]"
}

# ── Check result upload ─────────────────────────────────────

proc upload_check_results {design_name} {
    # Convert check_results to JSON and POST to server
    set results_json [results_to_json $design_name]
    set resp [http_post "/api/v1/check-results/upload" $results_json]
    puts "Results uploaded to server."
    return $resp
}

proc results_to_json {design_name} {
    set result_items [list]
    foreach result $::check_results {
        set findings_json [list]
        foreach f [dict get $result findings] {
            lappend findings_json [format {{"message":%s,"refdes":%s,"net":%s,"page":%s}} \
                [json_escape [dict get $f message]] \
                [json_escape [dict get $f refdes]] \
                [json_escape [dict get $f net]] \
                [json_escape [dict get $f page]]]
        }
        lappend result_items [format {{"rule_id":%s,"severity":%s,"status":%s,"findings":[%s]}} \
            [json_escape [dict get $result rule_id]] \
            [json_escape [dict get $result severity]] \
            [json_escape [dict get $result status]] \
            [join $findings_json ,]]
    }

    return [format {{"design_name":%s,"source":"orcad_tcl","results":[%s]}} \
        [json_escape $design_name] \
        [join $result_items ,]]
}

# ── Script download (OTA) ───────────────────────────────────

proc fetch_ota_manifest {} {
    return [http_get "/api/v1/scripts/ota/manifest"]
}

proc download_script {script_id} {
    return [http_get "/api/v1/scripts/ota/download/$script_id"]
}

# ── AI Agent chat ────────────────────────────────────────────

proc agent_chat {session_id message} {
    set body [format {{"session_id":%s,"message":%s}} \
        [json_escape $session_id] \
        [json_escape $message]]
    return [http_post "/api/v1/agent/chat" $body]
}

proc agent_save_script {session_id name code {category "custom"}} {
    set body [format {{"session_id":%s,"name":%s,"code":%s,"category":%s}} \
        [json_escape $session_id] \
        [json_escape $name] \
        [json_escape $code] \
        [json_escape $category]]
    return [http_post "/api/v1/agent/save" $body]
}
