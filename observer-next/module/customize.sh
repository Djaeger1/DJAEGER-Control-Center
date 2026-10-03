#!/system/bin/sh
ui_print "- DJAEGER AI Adaptive"
ui_print "- Device-first adaptive engine"
ui_print "- Observe -> Learn -> Validate -> Shadow -> Local Execute -> Readback -> Learn"
ui_print "- Cloud hardware authority: NONE"
ui_print "- SYSFS authority: local gated executor only"
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm_recursive "$MODPATH/bin" 0 0 0755 0755
