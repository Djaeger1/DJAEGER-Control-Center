#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"
PIDFILE="$STATE/launcher.pid"
BOOTLOG="$STATE/boot.log"

mkdir -p "$STATE"
chmod 700 "$STATE"

while [ "$(getprop sys.boot_completed)" != "1" ]; do
  sleep 3
done
sleep 8

[ -f "$STATE/DISABLED" ] && exit 0

if [ -f "$PIDFILE" ]; then
  OLD="$(cat "$PIDFILE" 2>/dev/null)"
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    exit 0
  fi
fi

echo "$(date '+%F %T') SERVICE=START" >> "$BOOTLOG"
sh "$MODDIR/bin/djaeger-remote-launcher.sh" >>"$BOOTLOG" 2>&1 &
echo $! > "$PIDFILE"
chmod 600 "$PIDFILE"
