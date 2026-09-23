#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"
PIDFILE="$STATE/launcher.pid"

mkdir -p "$STATE"

if [ -f "$STATE/DISABLED" ]; then
  rm -f "$STATE/DISABLED"
  echo "DJAEGER Remote: ENABLED"
  "$MODDIR/service.sh"
  exit 0
fi

touch "$STATE/DISABLED"
chmod 600 "$STATE/DISABLED"

if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE" 2>/dev/null)"
  [ -n "$PID" ] && kill "$PID" 2>/dev/null
fi

if [ -f "$STATE/agent.pid" ]; then
  PID="$(cat "$STATE/agent.pid" 2>/dev/null)"
  [ -n "$PID" ] && kill "$PID" 2>/dev/null
fi

echo "DJAEGER Remote: DISABLED"
