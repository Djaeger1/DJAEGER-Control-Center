#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"
for F in "$STATE/agent.pid" "$STATE/launcher.pid"; do
  [ -f "$F" ] || continue
  P="$(cat "$F" 2>/dev/null)"
  [ -n "$P" ] && kill "$P" 2>/dev/null || true
done
exit 0
