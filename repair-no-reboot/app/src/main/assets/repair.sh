#!/system/bin/sh
# DJAEGER NO-REBOOT RECOVERY1
# Scope: restore Railway updater transport, reassert Arcane GAME registry authority,
# refresh controller/session publication. Does NOT replace controller/predictor/profile map.
M=/data/adb/modules/djaeger_game_stabilizer
P=/data/adb/djaeger_ai
R="$P/railway"
UP="$M/system/bin/djaeger-railway-updater"
GR="$M/system/bin/djaeger-game-registry"
AUD="$M/system/bin/djaeger-live-audit"
BR="$M/system/bin/djaeger-railway-bridge"
CFP="$M/system/bin/djaeger-cc-freshness-patch"
GOOD_SHA=00a05a5c3a2062331e3948b260c0439ab25fb13e69031c0a119a43457834b41f

fail(){ echo "STATUS=FAIL"; echo "REASON=$1"; exit 1; }
qget(){ [ -r "$1" ] || return 0; awk -F= -v k="$2" '$1==k{v=substr($0,index($0,"=")+1);gsub(/^[[:space:]\047\042]+|[[:space:]\047\042]+$/,"",v);print v;exit}' "$1" 2>/dev/null; }
proc_is(){ _p="$1"; _n="$2"; case "$_p" in ''|*[!0-9]*) return 1;; esac; [ "$_p" -gt 1 ] 2>/dev/null && kill -0 "$_p" 2>/dev/null || return 1; _c="$(tr '\000' ' ' <"/proc/$_p/cmdline" 2>/dev/null)"; case "$_c" in *"$_n"*) return 0;; *) return 1;; esac; }

[ -d "$M" ] || fail MODULE_NOT_FOUND
VER="$(sed -n 's/^version=//p' "$M/module.prop" 2>/dev/null | head -1)"
case "$VER" in *VC129659*R89COMFORT2*) :;; *) fail "UNEXPECTED_MODULE=$VER";; esac
mkdir -p "$R" 2>/dev/null || fail RAILWAY_STATE_UNAVAILABLE
chmod 700 "$R" 2>/dev/null || true

CFG="$P/railway.conf"; DEF="$M/system/etc/djaeger/railway/railway.conf"
EP="$(qget "$CFG" ENDPOINT)"; [ -n "$EP" ] || EP="$(qget "$DEF" ENDPOINT)"
TOK="$(qget "$CFG" ACCESS_TOKEN)"; [ -n "$TOK" ] || TOK="$(qget "$DEF" ACCESS_TOKEN)"
case "$EP" in https://*) :;; *) fail RAILWAY_ENDPOINT_INVALID;; esac
[ -n "$TOK" ] || fail RAILWAY_TOKEN_MISSING
command -v curl >/dev/null 2>&1 || fail CURL_MISSING
command -v sha256sum >/dev/null 2>&1 || fail SHA256SUM_MISSING

STAGE="$R/recovery1.updater.$$"
URL="${EP%/}/v1/device/update/file/djaeger-railway-updater-predrestart1"
HTTP="$(curl -4 --http1.1 --connect-timeout 5 -m 15 -sS -o "$STAGE" -w '%{http_code}' -H "Authorization: Bearer $TOK" "$URL" 2>/dev/null)"
if [ "$HTTP" != 200 ]; then
  HTTP="$(curl --http1.1 --connect-timeout 5 -m 15 -sS -o "$STAGE" -w '%{http_code}' -H "Authorization: Bearer $TOK" "$URL" 2>/dev/null)"
fi
unset TOK
[ "$HTTP" = 200 ] || { rm -f "$STAGE"; fail "UPDATER_DOWNLOAD_HTTP_$HTTP"; }
GOT="$(sha256sum "$STAGE" 2>/dev/null | awk '{print $1}')"
[ "$GOT" = "$GOOD_SHA" ] || { rm -f "$STAGE"; fail UPDATER_HASH_MISMATCH; }
DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$STAGE" selftest >/dev/null 2>&1 || { rm -f "$STAGE"; fail UPDATER_STAGE_SELFTEST; }

BAK="$R/updater.pre_noreboot_recovery1"
[ -f "$UP" ] && cp -pf "$UP" "$BAK" 2>/dev/null || true
cp -f "$STAGE" "$UP.new.$$" 2>/dev/null && chmod 755 "$UP.new.$$" 2>/dev/null && mv -f "$UP.new.$$" "$UP" || { rm -f "$STAGE"; fail UPDATER_INSTALL_FAILED; }
rm -f "$STAGE"
DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$UP" selftest >/dev/null 2>&1 || {
  [ -f "$BAK" ] && cp -pf "$BAK" "$UP" 2>/dev/null && chmod 755 "$UP" 2>/dev/null
  fail UPDATER_INSTALLED_SELFTEST
}

[ -x "$GR" ] || fail GAME_REGISTRY_HELPER_MISSING
printf 'sts.al\nArcane Legends\n' | DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$GR" add-stdin >/dev/null 2>&1 || fail ARCANE_REGISTRY_REPAIR_FAILED
awk -F '\t' '$1=="sts.al"{f=1}END{exit !f}' "$P/custom_games.tsv" 2>/dev/null || fail ARCANE_GAME_REGISTRY_MISSING
if awk -F '\t' '$1=="sts.al"{f=1}END{exit !f}' "$P/workload/app_registry.tsv" 2>/dev/null; then fail ARCANE_STILL_IN_APP_REGISTRY; fi

OLDUP="$(cat "$R/updater.pid" 2>/dev/null)"
if proc_is "$OLDUP" djaeger-railway-updater; then kill "$OLDUP" 2>/dev/null || true; sleep 1; fi
rm -f "$R/updater.pid" 2>/dev/null
nohup sh "$UP" daemon >"$R/updater.recovery1.log" 2>&1 </dev/null &
_i=0; UP_LIVE=NO
while [ "$_i" -lt 10 ]; do
  NP="$(cat "$R/updater.pid" 2>/dev/null)"
  if proc_is "$NP" djaeger-railway-updater; then UP_LIVE=YES; break; fi
  sleep 1; _i=$((_i+1))
done
[ "$UP_LIVE" = YES ] || fail UPDATER_DAEMON_NOT_LIVE

CTRL_ACTION=KEPT
if [ ! -s "$P/session_game" ]; then
  CP="$(cat "$P/controller.pid" 2>/dev/null)"
  if proc_is "$CP" djaeger_game_stabilizer/controller.sh; then
    kill "$CP" 2>/dev/null || true
    CTRL_ACTION=RESTART_REQUESTED
  fi
  SP="$(cat "$P/supervisor.pid" 2>/dev/null)"
  if ! proc_is "$SP" djaeger_game_stabilizer/supervisor.sh; then
    rm -f "$P/supervisor.pid" 2>/dev/null; rm -rf "$P/supervisor.lock" 2>/dev/null
    nohup sh "$M/supervisor.sh" >"$M/supervisor.recovery1.log" 2>&1 </dev/null &
  fi
  _i=0
  while [ "$_i" -lt 20 ]; do
    NP="$(cat "$P/controller.pid" 2>/dev/null)"
    if proc_is "$NP" djaeger_game_stabilizer/controller.sh; then CTRL_ACTION=RESTARTED; break; fi
    sleep 1; _i=$((_i+1))
  done
  [ "$CTRL_ACTION" = RESTARTED ] || fail CONTROLLER_RESTART_FAILED
fi

_i=0; while [ ! -s "$P/cc_snapshot" ] && [ "$_i" -lt 10 ]; do sleep 1; _i=$((_i+1)); done
[ -x "$CFP" ] && DJAEGER_STATE_DIR="$P" sh "$CFP" >/dev/null 2>&1 || true
[ -x "$AUD" ] && DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$AUD" run >/dev/null 2>&1 || true
[ -x "$BR" ] && DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$BR" once >/dev/null 2>&1 || true

echo "STATUS=PASS"
echo "MODULE=$VER"
echo "UPDATER_SHA=$(sha256sum "$UP" 2>/dev/null | awk '{print $1}')"
echo "UPDATER_DAEMON=LIVE"
echo "ARCANE_GAME_REGISTRY=PASS"
echo "ARCANE_APP_CONFLICT=NONE"
echo "CONTROLLER_ACTION=$CTRL_ACTION"
echo "CONTROLLER_BINARY=UNCHANGED"
echo "PREDICTOR_BINARY=UNCHANGED"
echo "PROFILE_MAP=UNCHANGED"
echo "NO_REBOOT=YES"
echo "NO_FLASH=YES"
