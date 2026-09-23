#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"
mkdir -p "$STATE"
chmod 700 "$STATE"

if [ -f "$STATE/DISABLED" ]; then
  rm -f "$STATE/DISABLED"
  cmd notification post -S bigtext -t "DJAEGER Remote" djaeger_remote "ENABLED — starting root bridge." >/dev/null 2>&1 || true
  sh "$MODDIR/service.sh" >/dev/null 2>&1 &
else
  touch "$STATE/DISABLED"
  chmod 600 "$STATE/DISABLED"
  for F in "$STATE/agent.pid" "$STATE/launcher.pid"; do
    [ -f "$F" ] || continue
    P="$(cat "$F" 2>/dev/null)"
    [ -n "$P" ] && kill "$P" 2>/dev/null || true
  done
  cmd notification post -S bigtext -t "DJAEGER Remote" djaeger_remote "DISABLED — remote root bridge stopped." >/dev/null 2>&1 || true
fi
