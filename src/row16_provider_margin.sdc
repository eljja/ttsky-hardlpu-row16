# Implementation-only reserve for RC estimation and antenna diode loads.
# Final extracted STA uses the unmodified provider fallback SDC.
source $::env(SCRIPTS_DIR)/base.sdc
set_max_transition 0.4 [current_design]
set_max_fanout 8 [current_design]
