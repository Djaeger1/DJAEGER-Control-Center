#!/system/bin/sh
MODDIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$MODDIR/state"
NODE="$MODDIR/runtime/node"
AGENT="$MODDIR/agent/djaeger-rdc-agent.mjs"
LOG="$STATE/remote.log"
RUNLOG="$STATE/agent-current.log"
STATUS="$STATE/status.env"
SESSION="$STATE/session.json"

[ -f "$MODDIR/config.env" ] && . "$MODDIR/config.env"
REMOTE_BASE="${REMOTE_BASE:-https://mcp.desktopcommander.app}"
RESTART_DELAY_SEC="${RESTART_DELAY_SEC:-10}"
DEVICE_NAME="${DEVICE_NAME:-DJAEGER-Android}"

mkdir -p "$STATE" "$STATE/home" "$STATE/tmp"
chmod 700 "$STATE" "$STATE/home" "$STATE/tmp"
touch "$LOG"
chmod 600 "$LOG"

write_status() {
  {
    echo "STATE=$1"
    echo "DETAIL=$2"
    echo "UPDATED_AT=$(date '+%F %T')"
  } > "$STATUS"
  chmod 600 "$STATUS"
}

notify() {
  cmd notification post -S bigtext -t "DJAEGER Remote" djaeger_remote "$1" >/dev/null 2>&1 || true
}

if [ ! -x "$NODE" ]; then
  write_status "RUNTIME_NOT_FOUND" "bundled Node runtime missing"
  notify "RUNTIME_NOT_FOUND — bundled Node runtime missing."
  exit 20
fi

if [ ! -f "$AGENT" ]; then
  write_status "AGENT_NOT_FOUND" "Android RDC agent missing"
  notify "AGENT_NOT_FOUND — Android RDC agent missing."
  exit 21
fi

# One-time migration from the development pairing/session locations.
if [ ! -f "$SESSION" ]; then
  for OLD in     /data/local/tmp/djaeger-rdc-auth/session.json     "$STATE/home/.desktop-commander-device/device.json"
  do
    if [ -f "$OLD" ]; then
      cp -f "$OLD" "$SESSION"
      chmod 600 "$SESSION"
      echo "$(date '+%F %T') SESSION=MIGRATED from=$OLD" >> "$LOG"
      break
    fi
  done
fi

export HOME="$STATE/home"
export TMPDIR="$STATE/tmp"
export MCP_SERVER_URL="$REMOTE_BASE"
export DJAEGER_RDC_SESSION="$SESSION"
export DJAEGER_STATUS_PATH="$STATUS"
export DJAEGER_DEVICE_NAME="$DEVICE_NAME"
export PATH="/data/adb/ksu/bin:/data/adb/magisk:/system/bin:/system/xbin:/vendor/bin:/product/bin"

FAILS=0
while [ ! -f "$STATE/DISABLED" ]; do
  : > "$RUNLOG"
  chmod 600 "$RUNLOG"
  write_status "STARTING" "launching Android RDC root bridge"

  "$NODE" "$AGENT" >"$RUNLOG" 2>&1 &
  PID=$!
  echo "$PID" > "$STATE/agent.pid"
  chmod 600 "$STATE/agent.pid"
  echo "$(date '+%F %T') AGENT=START pid=$PID" >> "$LOG"

  wait "$PID"
  RC=$?
  rm -f "$STATE/agent.pid"

  {
    echo "===== $(date '+%F %T') agent exit rc=$RC ====="
    tail -n 300 "$RUNLOG" 2>/dev/null
    echo
  } >> "$LOG"

  [ -f "$STATE/DISABLED" ] && break

  FAILS=$((FAILS + 1))
  DELAY="$RESTART_DELAY_SEC"
  [ "$FAILS" -ge 3 ] && DELAY=30
  write_status "RESTARTING" "agent exited rc=$RC retry in ${DELAY}s"
  sleep "$DELAY"

  # Bound historical log growth on an unattended device.
  SIZE="$(wc -c < "$LOG" 2>/dev/null)"
  if [ -n "$SIZE" ] && [ "$SIZE" -gt 1048576 ]; then
    tail -c 524288 "$LOG" > "$LOG.tmp" 2>/dev/null && mv -f "$LOG.tmp" "$LOG"
    chmod 600 "$LOG"
  fi
done

write_status "DISABLED" "remote bridge disabled by kill-switch"
