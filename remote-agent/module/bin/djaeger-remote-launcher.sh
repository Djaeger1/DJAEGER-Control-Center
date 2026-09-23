#!/system/bin/sh
MODDIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$MODDIR/state"
LOG="$STATE/remote.log"
RUNLOG="$STATE/agent-current.log"
STATUS="$STATE/status.env"
PAIR_MARK="$STATE/pair-browser-opened"
ONLINE_MARK="$STATE/online-notified"
CFG="$STATE/home/.desktop-commander-device/device.json"

# shellcheck disable=SC1091
[ -f "$MODDIR/config.env" ] && . "$MODDIR/config.env"
DC_VERSION="${DC_VERSION:-0.2.51}"
RESTART_DELAY_SEC="${RESTART_DELAY_SEC:-20}"
NETWORK_RETRY_SEC="${NETWORK_RETRY_SEC:-60}"
HTTP_RETRY_SEC="${HTTP_RETRY_SEC:-180}"
FORBIDDEN_RETRY_SEC="${FORBIDDEN_RETRY_SEC:-900}"
REMOTE_BASE="${REMOTE_BASE:-https://mcp.desktopcommander.app}"
DEBUG_MODE="${DEBUG_MODE:-0}"

mkdir -p "$STATE/home" "$STATE/tmp" "$STATE/npm-cache"
chmod 700 "$STATE" "$STATE/home" "$STATE/tmp" "$STATE/npm-cache"
touch "$LOG"
chmod 600 "$LOG"

set_status() {
  CODE="$1"
  DETAIL="$2"
  {
    echo "STATE=$CODE"
    echo "DETAIL=$DETAIL"
    echo "UPDATED_AT=$(date '+%F %T')"
  } > "$STATUS"
  chmod 600 "$STATUS"
}

notify_status() {
  MSG="$1"
  cmd notification post -S bigtext -t "DJAEGER Remote" djaeger_remote "$MSG" >/dev/null 2>&1 || true
}

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
  set_status "RUNTIME_NOT_FOUND" "npx runtime tidak ditemukan"
  echo "$(date '+%F %T') ERROR runtime=npx_not_found" >> "$LOG"
  notify_status "RUNTIME_NOT_FOUND — Node/npx tidak ditemukan."
  exit 20
fi

BIN_DIR="$(dirname "$NPX")"
PREFIX="$(dirname "$BIN_DIR")"
NODE="$BIN_DIR/node"
[ -x "$NODE" ] || NODE="$(command -v node 2>/dev/null)"

if [ -z "$NODE" ] || [ ! -x "$NODE" ]; then
  set_status "NODE_NOT_FOUND" "node runtime tidak ditemukan"
  echo "$(date '+%F %T') ERROR runtime=node_not_found npx=$NPX" >> "$LOG"
  notify_status "NODE_NOT_FOUND — runtime Node tidak ditemukan."
  exit 21
fi

export HOME="$STATE/home"
export TMPDIR="$STATE/tmp"
export NPM_CONFIG_CACHE="$STATE/npm-cache"
export PREFIX="$PREFIX"
export PATH="$BIN_DIR:$PREFIX/bin:/system/bin:/system/xbin:/vendor/bin:/product/bin"
export DEBUG_MODE="$([ "$DEBUG_MODE" = "1" ] && echo true || echo false)"
export MCP_SERVER_URL="$REMOTE_BASE"

extract_pairing_url() {
  awk '
    /Verify this device in your browser:/ {
      if (getline > 0) {
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
        if ($0 ~ /^https:\/\//) print $0
      }
    }
  ' "$RUNLOG" 2>/dev/null | tail -n 1
}

open_pairing_if_needed() {
  [ -f "$CFG" ] && return 0
  [ -f "$PAIR_MARK" ] && return 0

  URL="$(extract_pairing_url)"
  [ -n "$URL" ] || return 0

  if am start -a android.intent.action.VIEW -d "$URL" >/dev/null 2>&1; then
    touch "$PAIR_MARK"
    chmod 600 "$PAIR_MARK"
    set_status "PAIRING_REQUIRED" "halaman pairing dibuka otomatis"
    notify_status "PAIRING_REQUIRED — setujui halaman verifikasi yang terbuka."
    echo "$(date '+%F %T') PAIRING_BROWSER=OPENED" >> "$LOG"
  else
    set_status "PAIR_OPEN_FAILED" "Android gagal membuka URL pairing"
    notify_status "PAIR_OPEN_FAILED — Android gagal membuka halaman pairing."
  fi
}

classify_exit() {
  if grep -q "Failed to fetch Supabase config: Forbidden" "$RUNLOG" 2>/dev/null || grep -q "403" "$RUNLOG" 2>/dev/null; then
    set_status "BLOCKED_403" "Remote Desktop Commander menolak endpoint Android"
    notify_status "BLOCKED_403 — endpoint Remote Desktop Commander menolak Android. Agent akan mencoba lagi nanti."
    echo "$FORBIDDEN_RETRY_SEC"
    return
  fi

  if grep -qiE "ENOTFOUND|EAI_AGAIN|network|fetch failed|ECONNRESET|ETIMEDOUT" "$RUNLOG" 2>/dev/null; then
    set_status "NETWORK_FAIL" "koneksi agent gagal"
    notify_status "NETWORK_FAIL — agent belum bisa mencapai server."
    echo "$NETWORK_RETRY_SEC"
    return
  fi

  if grep -qiE "Failed to fetch Supabase config|HTTP [45][0-9][0-9]" "$RUNLOG" 2>/dev/null; then
    set_status "HTTP_FAIL" "server remote mengembalikan error HTTP"
    notify_status "HTTP_FAIL — server remote menolak startup agent."
    echo "$HTTP_RETRY_SEC"
    return
  fi

  set_status "AGENT_EXIT" "agent berhenti sebelum online"
  notify_status "AGENT_EXIT — agent berhenti sebelum online."
  echo "$RESTART_DELAY_SEC"
}

while [ ! -f "$STATE/DISABLED" ]; do
  : > "$RUNLOG"
  chmod 600 "$RUNLOG"
  rm -f "$ONLINE_MARK"

  if [ ! -f "$CFG" ]; then
    rm -f "$PAIR_MARK"
  fi

  set_status "STARTING" "menjalankan Remote Desktop Commander"
  echo "$(date '+%F %T') AGENT=START version=$DC_VERSION npx=$NPX" >> "$LOG"

  "$NPX" --yes "@wonderwhy-er/desktop-commander@$DC_VERSION" remote > "$RUNLOG" 2>&1 &
  AGENT_PID=$!
  echo "$AGENT_PID" > "$STATE/agent.pid"
  chmod 600 "$STATE/agent.pid"

  while kill -0 "$AGENT_PID" 2>/dev/null; do
    open_pairing_if_needed

    if grep -q "Device ready:" "$RUNLOG" 2>/dev/null && [ ! -f "$ONLINE_MARK" ]; then
      touch "$ONLINE_MARK"
      chmod 600 "$ONLINE_MARK"
      set_status "ONLINE" "agent remote siap menerima command"
      notify_status "ONLINE — DJAEGER Remote siap."
      echo "$(date '+%F %T') AGENT=ONLINE" >> "$LOG"
    fi

    if [ -f "$CFG" ]; then
      chmod 600 "$CFG" 2>/dev/null
    fi

    [ -f "$STATE/DISABLED" ] && kill "$AGENT_PID" 2>/dev/null
    sleep 2
  done

  wait "$AGENT_PID"
  RC=$?
  rm -f "$STATE/agent.pid"

  {
    echo "===== $(date '+%F %T') agent exit rc=$RC ====="
    cat "$RUNLOG" 2>/dev/null
    echo
  } >> "$LOG"

  [ -f "$STATE/DISABLED" ] && break

  DELAY="$(classify_exit)"
  echo "$(date '+%F %T') AGENT=EXIT rc=$RC retry=${DELAY}s" >> "$LOG"
  sleep "$DELAY"
done
