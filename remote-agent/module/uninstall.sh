#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"

if [ -f "$STATE/agent.pid" ]; then
  PID="$(cat "$STATE/agent.pid" 2>/dev/null)"
  [ -n "$PID" ] && kill "$PID" 2>/dev/null
fi

if [ -f "$STATE/launcher.pid" ]; then
  PID="$(cat "$STATE/launcher.pid" 2>/dev/null)"
  [ -n "$PID" ] && kill "$PID" 2>/dev/null
fi

rm -f "$STATE/agent.pid" "$STATE/launcher.pid"
