#!/system/bin/sh
ROOT="${HERMES_ROOT:-/data/adb/hermes_work}"
REL="${HERMES_RELEASE:-$ROOT/releases/v0.2.0-control-center}"
PID="$ROOT/state/workd.pid"; LOG="$ROOT/logs/workd.log"
mkdir -p "$ROOT/data/research" "$ROOT/data/knowledge" "$ROOT/data/database" "$ROOT/state" "$ROOT/logs" "$ROOT/backups" "$ROOT/updates"
if [ -f "$PID" ] && kill -0 "$(cat "$PID" 2>/dev/null)" 2>/dev/null; then exit 0; fi
nohup "$REL/bin/workd" --root "$ROOT" --release "$REL" >>"$LOG" 2>&1 &
echo $! > "$PID"
