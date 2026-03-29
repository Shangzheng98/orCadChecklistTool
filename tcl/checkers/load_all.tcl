# Load all checker scripts
set _checker_dir [file dirname [info script]]

source [file join $_checker_dir duplicate_refdes.tcl]
source [file join $_checker_dir missing_attributes.tcl]
source [file join $_checker_dir unconnected_pins.tcl]
source [file join $_checker_dir footprint_validation.tcl]
source [file join $_checker_dir power_net_naming.tcl]
source [file join $_checker_dir net_naming.tcl]
source [file join $_checker_dir single_pin_nets.tcl]
