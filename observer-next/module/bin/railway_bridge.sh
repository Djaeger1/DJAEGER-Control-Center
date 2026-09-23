#!/system/bin/sh
# Read-only telemetry bridge to the dedicated DJAEGER AI clean core.
ROOT="$1"
BIN_DIR="${0%/*}"
if [ "${2:-once}" = daemon ] && [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim railway_bridge
fi
CFG="$ROOT/config/railway.env"
SNAP="$ROOT/runtime/snapshot.env"
STATE="$ROOT/runtime/railway.env"
MODULE_PROP="${BIN_DIR%/bin}/module.prop"
NEURON="$ROOT/config/hermes_neuron_live.env"
DEFAULT_URL="https://djaeger-ai-core-production-736f.up.railway.app"
kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
legacy_exact(){
  _k="$1"; _f="$2"
  sed -n "s/^[[:space:]]*$_k[[:space:]]*=[[:space:]]*['\"]\{0,1\}\([^'\"[:space:]]\{1,1024\}\).*/\1/p" "$_f" 2>/dev/null | head -n1
}
recover_legacy_railway(){
  _token="$(kv DJAEGER_ACCESS_TOKEN "$CFG")"
  _url="$(kv DJAEGER_RAILWAY_URL "$CFG")"
  [ -n "$_token" ] && [ -n "$_url" ] && return 0
  for _rf in /data/adb/djaeger_ai/railway.conf /data/adb/modules/djaeger_game_stabilizer/system/etc/djaeger/railway/railway.conf; do
    [ -r "$_rf" ] || continue
    [ -n "$_token" ] || _token="$(legacy_exact DJAEGER_ACCESS_TOKEN "$_rf")"
    [ -n "$_token" ] || _token="$(legacy_exact ACCESS_TOKEN "$_rf")"
    [ -n "$_url" ] || _url="$(legacy_exact DJAEGER_RAILWAY_URL "$_rf")"
    [ -n "$_url" ] || _url="$(legacy_exact ENDPOINT "$_rf")"
  done
  [ -n "$_token" ] || return 1
  [ -n "$_url" ] || _url="$DEFAULT_URL"
  _tmp="$CFG.tmp.$$"
  {
    printf 'DJAEGER_ACCESS_TOKEN=%s\n' "$_token"
    printf 'DJAEGER_RAILWAY_URL=%s\n' "$_url"
  } > "$_tmp" || return 1
  chmod 600 "$_tmp"; mv -f "$_tmp" "$CFG"
}
clean(){ printf '%s' "$1" | tr '\r\n\t' '   ' | tr -cd 'A-Za-z0-9._:+/%=,@ -' | cut -c1-160; }
publish(){ _t="$STATE.tmp.$$"; { echo "RAILWAY_STATE=$1"; echo "RAILWAY_HTTP=${2:-NA}"; echo "UPDATED_AT=$(date +%s)"; } > "$_t"; chmod 600 "$_t"; mv -f "$_t" "$STATE"; }
send_once(){
  [ -r "$SNAP" ] || { publish WAITING; return 0; }
  TOKEN="$(kv DJAEGER_ACCESS_TOKEN "$CFG")"
  if [ -z "$TOKEN" ]; then recover_legacy_railway >/dev/null 2>&1 || true; TOKEN="$(kv DJAEGER_ACCESS_TOKEN "$CFG")"; fi
  [ -n "$TOKEN" ] || { publish NO_TOKEN; return 0; }
  URL="$(kv DJAEGER_RAILWAY_URL "$CFG")"; [ -n "$URL" ] || URL="$DEFAULT_URL"
  case "$URL" in https://*) :;; *) publish INVALID_URL; return 1;; esac
  body="$ROOT/runtime/.railway_payload.$$"
  _ver="$(sed -n 's/^version=//p' "$MODULE_PROP" 2>/dev/null | head -n1)"
  _vc="$(sed -n 's/^versionCode=//p' "$MODULE_PROP" 2>/dev/null | head -n1)"
  _nused="$(kv USED_EST "$NEURON")"; [ -n "$_nused" ] || _nused=0
  _nlimit="$(kv LIMIT "$NEURON")"; [ -n "$_nlimit" ] || _nlimit=10000
  _nday="$(kv UTC_DAY "$NEURON")"
  printf '{"schema":"DJAEGER_AI_TELEMETRY_V1","device_id":"%s","at":%s,"module_version":"%s","module_version_code":"%s","package":"%s","cpu_little_khz":"%s","cpu_big_khz":"%s","gpu_hz":"%s","skin_temp_c":"%s","battery_temp_c":"%s","cpu_temp_c":"%s","gpu_temp_c":"%s","power_mw":"%s","fps":"%s","jank_pct":"%s","neuron_local_estimate_present":"YES","neuron_used_est":"%s","neuron_limit":"%s","neuron_epoch_day":"%s","source":"LOCAL_OBSERVER"}'     "$(clean "$(kv DEVICE_ID "$ROOT/config/identity.env")")" "$(date +%s)" "$(clean "$_ver")" "$(clean "$_vc")" "$(clean "$(kv ACTIVE_PACKAGE "$SNAP")")"     "$(clean "$(kv LITTLE_CUR_KHZ "$SNAP")")" "$(clean "$(kv BIG_CUR_KHZ "$SNAP")")" "$(clean "$(kv GPU_CUR_HZ "$SNAP")")"     "$(clean "$(kv SKIN_TEMP_C "$SNAP")")" "$(clean "$(kv BATTERY_TEMP_C "$SNAP")")" "$(clean "$(kv CPU_TEMP_C "$SNAP")")" "$(clean "$(kv GPU_TEMP_C "$SNAP")")"     "$(clean "$(kv POWER_MW "$SNAP")")" "$(clean "$(kv FPS_EST "$SNAP")")" "$(clean "$(kv JANK_PCT "$SNAP")")" "$(clean "$_nused")" "$(clean "$_nlimit")" "$(clean "$_nday")" > "$body"
  curlcfg="$(mktemp "$ROOT/runtime/.railway_curl.XXXXXX" 2>/dev/null)"; [ -n "$curlcfg" ] || { rm -f "$body"; unset TOKEN; publish TEMPFILE_ERROR; return 1; }
  printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" > "$curlcfg"
  chmod 600 "$curlcfg"
  HTTP="$(curl -4 --http1.1 --connect-timeout 4 -m 8 -sS -o /dev/null -w '%{http_code}' -K "$curlcfg" -H 'Content-Type: application/json' --data-binary "@$body" "${URL%/}/v1/device/telemetry" 2>/dev/null)"; _rc=$?
  if [ "$_rc" -ne 0 ]; then
    HTTP="$(curl --http1.1 --connect-timeout 4 -m 8 -sS -o /dev/null -w '%{http_code}' -K "$curlcfg" -H 'Content-Type: application/json' --data-binary "@$body" "${URL%/}/v1/device/telemetry" 2>/dev/null)"
  fi
  rm -f "$curlcfg" "$body"; unset TOKEN
  [ "$HTTP" = 200 ] && publish CONNECTED "$HTTP" || publish OFFLINE "${HTTP:-000}"
}
case "${2:-once}" in once) send_once;; daemon) while :; do send_once >/dev/null 2>&1 || true; sleep 30; done;; *) exit 2;; esac
