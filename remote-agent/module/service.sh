#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"
PIDFILE="$STATE/launcher.pid"
BOOTLOG="$STATE/boot.log"

mkdir -p "$STATE"
chmod 700 "$STATE"
touch "$BOOTLOG"
chmod 600 "$BOOTLOG"

echo "$(date '+%F %T') service.sh entered" >> "$BOOTLOG"

while [ "$(getprop sys.boot_completed)" != "1" ]; do
  sleep 3
done
sleep 8

[ -f "$STATE/DISABLED" ] && {
  echo "$(date '+%F %T') disabled by kill-switch" >> "$BOOTLOG"
  exit 0
}

if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "$(date '+%F %T') launcher already alive pid=$OLD_PID" >> "$BOOTLOG"
    exit 0
  fi
  rm -f "$PIDFILE"
fi

# Run through /system/bin/sh so startup is robust even if a module manager
# strips executable bits while installing the ZIP.
sh "$MODDIR/bin/djaeger-remote-launcher.sh" >>"$BOOTLOG" 2>&1 &
PID=$!
echo "$PID" > "$PIDFILE"
chmod 600 "$PIDFILE"
echo "$(date '+%F %T') launcher started pid=$PID" >> "$BOOTLOG"
