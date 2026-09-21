#!/system/bin/sh
# Read-only telemetry bridge to the dedicated DJAEGER AI clean core.
ROOT="$1"
CFG="$ROOT/config/railway.env"
SNAP="$ROOT/runtime/snapshot.env"
STATE="$ROOT/runtime/railway.env"
DEFAULT_URL="__DJAEGER_CLEAN_RAILWAY_URL__"
kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
clean(){ printf '%s' "$1" | tr '\r\n\t' '   ' | tr -cd 'A-Za-z0-9._:+/%=,@ -' | cut -c1-160; }
publish(){ _t="$STATE.tmp.$$"; { echo "RAILWAY_STATE=$1"; echo "RAILWAY_HTTP=${2:-NA}"; echo "UPDATED_AT=$(date +%s)"; } > "$_t"; chmod 600 "$_t"; mv -f "$_t" "$STATE"; }
send_once(){
  [ -r "$SNAP" ] || { publish WAITING; return 0; }
  TOKEN="$(kv DJAEGER_ACCESS_TOKEN "$CFG")"; [ -n "$TOKEN" ] || { publish NO_TOKEN; return 0; }
  URL="$(kv DJAEGER_RAILWAY_URL "$CFG")"; [ -n "$URL" ] || URL="$DEFAULT_URL"
  case "$URL" in https://*) :;; *) publish INVALID_URL; return 1;; esac
  body="$ROOT/runtime/.railway_payload.$$"
  printf '{"schema":"DJAEGER_AI_TELEMETRY_V1","device_id":"%s","at":%s,"package":"%s","cpu_little_khz":"%s","cpu_big_khz":"%s","gpu_hz":"%s","skin_temp_c":"%s","battery_temp_c":"%s","cpu_temp_c":"%s","gpu_temp_c":"%s","power_mw":"%s","fps":"%s","jank_pct":"%s","source":"LOCAL_OBSERVER"}'     "$(clean "$(kv DEVICE_ID "$ROOT/config/identity.env")")" "$(date +%s)" "$(clean "$(kv ACTIVE_PACKAGE "$SNAP")")"     "$(clean "$(kv LITTLE_CUR_KHZ "$SNAP")")" "$(clean "$(kv BIG_CUR_KHZ "$SNAP")")" "$(clean "$(kv GPU_CUR_HZ "$SNAP")")"     "$(clean "$(kv SKIN_TEMP_C "$SNAP")")" "$(clean "$(kv BATTERY_TEMP_C "$SNAP")")" "$(clean "$(kv CPU_TEMP_C "$SNAP")")" "$(clean "$(kv GPU_TEMP_C "$SNAP")")"     "$(clean "$(kv POWER_MW "$SNAP")")" "$(clean "$(kv FPS_EST "$SNAP")")" "$(clean "$(kv JANK_PCT "$SNAP")")" > "$body"
  HTTP="$(curl --http1.1 --connect-timeout 4 -m 8 -sS -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" --data-binary "@$body" "${URL%/}/v1/device/telemetry" 2>/dev/null)"
  rm -f "$body"; unset TOKEN
  [ "$HTTP" = 200 ] && publish CONNECTED "$HTTP" || publish OFFLINE "${HTTP:-000}"
}
case "${2:-once}" in once) send_once;; daemon) while :; do send_once >/dev/null 2>&1 || true; sleep 30; done;; *) exit 2;; esac
