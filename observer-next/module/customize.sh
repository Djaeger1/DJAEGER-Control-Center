#!/system/bin/sh
ui_print "- DJAEGER AI Observer"
ui_print "- Observer-first engine; legacy profiles are not installed"
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm_recursive "$MODPATH/bin" 0 0 0755 0755
