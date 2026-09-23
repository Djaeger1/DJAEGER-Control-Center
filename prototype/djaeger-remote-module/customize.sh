#!/system/bin/sh
ui_print "- DJAEGER Remote Root Bridge v1.0.0"
ABI="$(getprop ro.product.cpu.abi)"
SDK="$(getprop ro.build.version.sdk)"
[ "$ABI" = "arm64-v8a" ] || abort "! Unsupported ABI: $ABI (arm64-v8a required)"
[ "$SDK" -ge 24 ] || abort "! Android API 24+ required"

set_perm "$MODPATH/service.sh" 0 0 0755
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
set_perm "$MODPATH/action.sh" 0 0 0755
set_perm "$MODPATH/uninstall.sh" 0 0 0755
set_perm "$MODPATH/bin/djaeger-remote-launcher.sh" 0 0 0755
set_perm "$MODPATH/runtime/node" 0 0 0755
set_perm "$MODPATH/agent/djaeger-rdc-agent.mjs" 0 0 0644
mkdir -p "$MODPATH/state" "$MODPATH/state/home" "$MODPATH/state/tmp"
chmod 700 "$MODPATH/state" "$MODPATH/state/home" "$MODPATH/state/tmp"
