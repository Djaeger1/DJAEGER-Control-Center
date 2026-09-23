#!/system/bin/sh
MODDIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$MODDIR/state"
LOG="$STATE/remote.log"
PAIR_MARK="$STATE/pair-browser-opened"
CFG="$STATE/home/.desktop-commander-device/device.json"

# shellcheck disable=SC1091
[ -f "$MODDIR/config.env" ] && . "$MODDIR/config.env"
DC_VERSION="${DC_VERSION:-0.2.51}"
RESTART_DELAY_SEC="${RESTART_DELAY_SEC:-15}"
DEBUG_MODE="${DEBUG_MODE:-0}"

mkdir -p "$STATE/home" "$STATE/tmp" "$STATE/npm-cache"
chmod 700 "$STATE" "$STATE/home" "$STATE/tmp" "$STATE/npm-cache"
touch "$LOG"
chmod 600 "$LOG"

find_npx() {
  for p in \
    /data/user/0/com.termoneplus/files/usr/bin/npx \
    /data/data/com.termoneplus/files/usr/bin/npx \
    /data/user/0/com.termoneplus/app_HOME/usr/bin/npx \
    /data/user/0/com.termoneplus/app_HOME/bin/npx \
    /data/user/0/com.termux/files/usr/bin/npx \
    /data/data/com.termux/files/usr/bin/npx
  do
    [ -x "$p" ] && { echo "$p"; return 0; }
  done

  # Narrow fallback search; never scan the whole device.
  for root in /data/user/0/com.termoneplus /data/data/com.termoneplus /data/user/0/com.termux /data/data/com.termux; do
    [ -d "$root" ] || continue
    p="$(find "$root" -type f -name npx -path '*/bin/npx' 2>/dev/null | head -n 1)"
    [ -n "$p" ] && { echo "$p"; return 0; }
  done
  return 1
}

NPX="$(find_npx)"
if [ -z "$NPX" ]; then
  echo "$(date '+%F %T') ERROR: npx runtime not found; agent not started." >> "$LOG"
  exit 20
fi

BIN_DIR="$(dirname "$NPX")"
PREFIX="$(dirname "$BIN_DIR")"

export HOME="$STATE/home"
export TMPDIR="$STATE/tmp"
export NPM_CONFIG_CACHE="$STATE/npm-cache"
export PREFIX="$PREFIX"
export PATH="$BIN_DIR:$PREFIX/bin:/system/bin:/system/xbin:/vendor/bin:/product/bin"
export DEBUG_MODE="$([ "$DEBUG_MODE" = "1" ] && echo true || echo false)"

open_pairing_if_needed() {
  [ -f "$CFG" ] && return 0
  [ -f "$PAIR_MARK" ] && return 0

  # The official agent prints verification_uri_complete. Open it once; the user
  # only approves the browser page and never copies a token/API key/device ID.
  URL="$(grep -Eo 'https://[^[:space:]]+' "$LOG" 2>/dev/null | grep 'desktopcommander\.app' | tail -n 1)"
  [ -n "$URL" ] || return 0

  am start -a android.intent.action.VIEW -d "$URL" >/dev/null 2>&1 && {
    touch "$PAIR_MARK"
    chmod 600 "$PAIR_MARK"
    echo "$(date '+%F %T') Pairing page opened automatically." >> "$LOG"
  }
}

while [ ! -f "$STATE/DISABLED" ]; do
  echo "$(date '+%F %T') Starting Desktop Commander remote agent v$DC_VERSION" >> "$LOG"

  "$NPX" --yes "@wonderwhy-er/desktop-commander@$DC_VERSION" remote >> "$LOG" 2>&1 &
  AGENT_PID=$!
  echo "$AGENT_PID" > "$STATE/agent.pid"
  chmod 600 "$STATE/agent.pid"

  while kill -0 "$AGENT_PID" 2>/dev/null; do
    open_pairing_if_needed
    if [ -f "$CFG" ]; then
      chmod 600 "$CFG" 2>/dev/null
    fi
    [ -f "$STATE/DISABLED" ] && kill "$AGENT_PID" 2>/dev/null
    sleep 2
  done

  wait "$AGENT_PID"
  RC=$?
  rm -f "$STATE/agent.pid"

  [ -f "$STATE/DISABLED" ] && break
  echo "$(date '+%F %T') Agent exited rc=$RC; retrying in ${RESTART_DELAY_SEC}s." >> "$LOG"
  sleep "$RESTART_DELAY_SEC"
done
