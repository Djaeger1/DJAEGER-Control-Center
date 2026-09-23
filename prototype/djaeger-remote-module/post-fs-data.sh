#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"
mkdir -p "$STATE" "$STATE/home" "$STATE/tmp"
chmod 700 "$STATE" "$STATE/home" "$STATE/tmp"
chmod 755 "$MODDIR/service.sh" "$MODDIR/post-fs-data.sh" "$MODDIR/action.sh" "$MODDIR/uninstall.sh" "$MODDIR/bin/djaeger-remote-launcher.sh" 2>/dev/null
chmod 755 "$MODDIR/runtime/node" 2>/dev/null
chmod 644 "$MODDIR/agent/djaeger-rdc-agent.mjs" 2>/dev/null
