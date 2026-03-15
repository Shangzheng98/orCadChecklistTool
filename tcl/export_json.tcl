# JSON serialization utilities for TCL
# Converts TCL dicts/lists to JSON format

proc to_json_string {str} {
    set str [string map {\\ \\\\ \" \\\" \n \\n \t \\t} $str]
    return "\"$str\""
}

proc to_json_bool {val} {
    if {$val} { return "true" } else { return "false" }
}

proc to_json_list {lst converter} {
    set items [list]
    foreach item $lst {
        lappend items [$converter $item]
    }
    return "\[[join $items ,]\]"
}

proc to_json_string_list {lst} {
    set items [list]
    foreach item $lst {
        lappend items [to_json_string $item]
    }
    return "\[[join $items ,]\]"
}

proc to_json_dict {d} {
    set items [list]
    dict for {key val} $d {
        lappend items "[to_json_string $key]: [to_json_string $val]"
    }
    return "\{[join $items ,]\}"
}

proc pin_to_json {pin} {
    set items [list]
    lappend items "\"number\": [to_json_string [dict get $pin number]]"
    lappend items "\"name\": [to_json_string [dict get $pin name]]"
    lappend items "\"type\": [to_json_string [dict get $pin type]]"
    lappend items "\"net\": [to_json_string [dict get $pin net]]"
    return "\{[join $items ,]\}"
}

proc connection_to_json {conn} {
    set items [list]
    lappend items "\"refdes\": [to_json_string [dict get $conn refdes]]"
    lappend items "\"pin_number\": [to_json_string [dict get $conn pin_number]]"
    lappend items "\"pin_name\": [to_json_string [dict get $conn pin_name]]"
    return "\{[join $items ,]\}"
}

proc component_to_json {comp} {
    set items [list]
    lappend items "\"refdes\": [to_json_string [dict get $comp refdes]]"
    lappend items "\"part_name\": [to_json_string [dict get $comp part_name]]"
    lappend items "\"value\": [to_json_string [dict get $comp value]]"
    lappend items "\"footprint\": [to_json_string [dict get $comp footprint]]"
    lappend items "\"part_number\": [to_json_string [dict get $comp part_number]]"
    lappend items "\"library\": [to_json_string [dict get $comp library]]"
    lappend items "\"page\": [to_json_string [dict get $comp page]]"
    lappend items "\"properties\": [to_json_dict [dict get $comp properties]]"
    lappend items "\"pins\": [to_json_list [dict get $comp pins] pin_to_json]"
    return "\{[join $items ,]\}"
}

proc net_to_json {net} {
    set items [list]
    lappend items "\"name\": [to_json_string [dict get $net name]]"
    lappend items "\"is_power\": [to_json_bool [dict get $net is_power]]"
    lappend items "\"connections\": [to_json_list [dict get $net connections] connection_to_json]"
    return "\{[join $items ,]\}"
}

proc unconnected_pin_to_json {upin} {
    set items [list]
    lappend items "\"refdes\": [to_json_string [dict get $upin refdes]]"
    lappend items "\"pin_number\": [to_json_string [dict get $upin pin_number]]"
    lappend items "\"pin_name\": [to_json_string [dict get $upin pin_name]]"
    return "\{[join $items ,]\}"
}

proc write_json_file {filepath data} {
    set fp [open $filepath w]
    fconfigure $fp -encoding utf-8
    puts $fp $data
    close $fp
}
