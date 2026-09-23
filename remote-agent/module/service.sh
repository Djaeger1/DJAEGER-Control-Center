#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"
PIDFILE="$STATE/launcher.pid"

mkdir -p "$STATE"
chmod 700 "$STATE"

# Wait until Android userspace/network has had time to come up.
while [ "$(getprop sys.boot_completed)" != "1" ]; do
  sleep 3
done
sleep 8

# User kill-switch. The module can remain installed while remote access stays off.
[ -f "$STATE/DISABLED" ] && exit 0

# Avoid duplicate launchers after service re-entry.
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    exit 0
  fi
fi

"$MODDIR/bin/djaeger-remote-launcher.sh" >/dev/null 2>&1 &
echo $! > "$PIDFILE"
chmod 600 "$PIDFILE"
