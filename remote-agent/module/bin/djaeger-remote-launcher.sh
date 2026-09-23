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
NETWORK_RETRY_SEC="${NETWORK_RETRY_SEC:-30}"
HTTP_RETRY_SEC="${HTTP_RETRY_SEC:-120}"
FORBIDDEN_RETRY_SEC="${FORBIDDEN_RETRY_SEC:-900}"
REMOTE_BASE="${REMOTE_BASE:-https://mcp.desktopcommander.app}"
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

  for root in /data/user/0/com.termoneplus /data/data/com.termoneplus /data/user/0/com.termux /data/data/com.termux; do
    [ -d "$root" ] || continue
    p="$(find "$root" -type f -name npx -path '*/bin/npx' 2>/dev/null | head -n 1)"
    [ -n "$p" ] && { echo "$p"; return 0; }
  done
  return 1
}

NPX="$(find_npx)"
if [ -z "$NPX" ]; then
  echo "$(date '+%F %T') ERROR runtime=npx_not_found" >> "$LOG"
  exit 20
fi

BIN_DIR="$(dirname "$NPX")"
PREFIX="$(dirname "$BIN_DIR")"
NODE="$BIN_DIR/node"
[ -x "$NODE" ] || NODE="$(command -v node 2>/dev/null)"

if [ -z "$NODE" ] || [ ! -x "$NODE" ]; then
  echo "$(date '+%F %T') ERROR runtime=node_not_found npx=$NPX" >> "$LOG"
  exit 21
fi

export HOME="$STATE/home"
export TMPDIR="$STATE/tmp"
export NPM_CONFIG_CACHE="$STATE/npm-cache"
export PREFIX="$PREFIX"
export PATH="$BIN_DIR:$PREFIX/bin:/system/bin:/system/xbin:/vendor/bin:/product/bin"
export DEBUG_MODE="$([ "$DEBUG_MODE" = "1" ] && echo true || echo false)"
export MCP_SERVER_URL="$REMOTE_BASE"

preflight_remote() {
  PREFLIGHT_URL="$REMOTE_BASE/api/mcp-info"
  STATUS="$("$NODE" -e '
const u=process.argv[1];
fetch(u,{redirect:"manual"})
  .then(r=>{console.log(r.status); process.exit(r.ok ? 0 : 10)})
  .catch(()=>{console.log("NETWORK_ERROR"); process.exit(20)})
' "$PREFLIGHT_URL" 2>>"$LOG")"
  RC=$?

  case "$RC:$STATUS" in
    0:2??)
      echo "$(date '+%F %T') PREFLIGHT=PASS http=$STATUS" >> "$LOG"
      return 0
      ;;
    10:403)
      echo "$(date '+%F %T') PREFLIGHT=BLOCKED http=403 backoff=${FORBIDDEN_RETRY_SEC}s" >> "$LOG"
      sleep "$FORBIDDEN_RETRY_SEC"
      return 1
      ;;
    10:*)
      echo "$(date '+%F %T') PREFLIGHT=HTTP_FAIL http=$STATUS backoff=${HTTP_RETRY_SEC}s" >> "$LOG"
      sleep "$HTTP_RETRY_SEC"
      return 1
      ;;
    *)
      echo "$(date '+%F %T') PREFLIGHT=NETWORK_FAIL status=$STATUS backoff=${NETWORK_RETRY_SEC}s" >> "$LOG"
      sleep "$NETWORK_RETRY_SEC"
      return 1
      ;;
  esac
}

open_pairing_if_needed() {
  [ -f "$CFG" ] && return 0
  [ -f "$PAIR_MARK" ] && return 0

  URL="$(grep -Eo 'https://[^[:space:]]+' "$LOG" 2>/dev/null | grep 'desktopcommander\.app' | tail -n 1)"
  [ -n "$URL" ] || return 0

  am start -a android.intent.action.VIEW -d "$URL" >/dev/null 2>&1 && {
    touch "$PAIR_MARK"
    chmod 600 "$PAIR_MARK"
    echo "$(date '+%F %T') PAIRING_BROWSER=OPENED" >> "$LOG"
  }
}

while [ ! -f "$STATE/DISABLED" ]; do
  preflight_remote || continue

  if [ ! -f "$CFG" ]; then
    rm -f "$PAIR_MARK"
  fi

  echo "$(date '+%F %T') AGENT=START version=$DC_VERSION" >> "$LOG"

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
  echo "$(date '+%F %T') AGENT=EXIT rc=$RC retry=${RESTART_DELAY_SEC}s" >> "$LOG"
  sleep "$RESTART_DELAY_SEC"
done
