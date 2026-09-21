#!/system/bin/sh
# DJAEGER_TRANSPORT_RECOVERY_V2
# One-time root-side repair for Adaptive VC202/203.
# No reboot, no flash, no CPU/GPU/sysfs writes.
ASSETS="$1"
ROOT=/data/adb/djaeger_observer
MOD=/data/adb/modules/djaeger_ai_observer
LEGACY=/data/adb/djaeger_ai
LEGACY_MOD=/data/adb/modules/djaeger_game_stabilizer
DEFAULT_URL=https://djaeger-ai-core-production-736f.up.railway.app
STAMP="$(date +%s)"
BACKUP="$ROOT/recovery/transport-recovery-v2.$STAMP"
RESULT="$ROOT/runtime/transport_recovery_v2.env"

fail(){
  echo "RECOVERY_RESULT=FAIL"
  echo "RECOVERY_REASON=$1"
  mkdir -p "$ROOT/runtime" 2>/dev/null
  { echo "RECOVERY_RESULT=FAIL"; echo "RECOVERY_REASON=$1"; echo "UPDATED_AT=$(date +%s)"; } >"$RESULT.tmp" 2>/dev/null && { chmod 600 "$RESULT.tmp"; mv -f "$RESULT.tmp" "$RESULT"; }
  exit 1
}
qget(){
  [ -r "$1" ] || return 0
  awk -F= -v k="$2" '$1==k{v=substr($0,index($0,"=")+1);gsub(/^[[:space:]\047\042]+|[[:space:]\047\042]+$/,"",v);print v;exit}' "$1" 2>/dev/null
}
setkv(){
  _file="$1"; _key="$2"; _val="$3"; _tmp="$_file.tmp.$$"
  mkdir -p "$(dirname "$_file")" 2>/dev/null || return 1
  [ -r "$_file" ] && awk -F= -v k="$_key" '$1!=k{print}' "$_file" >"$_tmp" || : >"$_tmp"
  printf '%s=%s\n' "$_key" "$_val" >>"$_tmp"
  chmod 600 "$_tmp" 2>/dev/null; mv -f "$_tmp" "$_file"
}
kill_updaters(){
  for _d in /proc/[0-9]*; do
    [ -r "$_d/cmdline" ] || continue
    _p="${_d##*/}"
    _cmd="$(tr '\000' ' ' <"$_d/cmdline" 2>/dev/null)"
    case "$_cmd" in
      *djaeger_ai_observer*remote_updater.sh*|*com.djaeger.recovery*remote_updater.sh*)
        [ "$_p" = "$$" ] || kill "$_p" 2>/dev/null || true
      ;;
    esac
  done
}

[ "$(id -u 2>/dev/null)" = 0 ] || fail ROOT_DENIED
[ -d "$MOD" ] || fail ADAPTIVE_MODULE_NOT_FOUND
grep -Fqx 'id=djaeger_ai_observer' "$MOD/module.prop" 2>/dev/null || fail WRONG_MODULE_ID
VC="$(sed -n 's/^versionCode=//p' "$MOD/module.prop" 2>/dev/null | head -1)"
case "$VC" in 202|203) :;; *) fail "UNSUPPORTED_MODULE_VC_$VC";; esac
[ -r "$ASSETS/remote_updater.sh" ] || fail UPDATER_ASSET_MISSING
sh -n "$ASSETS/remote_updater.sh" >/dev/null 2>&1 || fail UPDATER_ASSET_SYNTAX

mkdir -p "$ROOT/config" "$ROOT/runtime" "$ROOT/recovery" "$BACKUP" 2>/dev/null || fail STATE_DIR_FAILED
chmod 700 "$ROOT" "$ROOT/config" "$ROOT/runtime" "$ROOT/recovery" "$BACKUP" 2>/dev/null || true

CFG="$ROOT/config/railway.env"
TOKEN="$(qget "$CFG" DJAEGER_ACCESS_TOKEN)"
URL="$(qget "$CFG" DJAEGER_RAILWAY_URL)"
for f in "$LEGACY/railway.conf" "$LEGACY_MOD/system/etc/djaeger/railway/railway.conf"; do
  [ -r "$f" ] || continue
  [ -n "$TOKEN" ] || TOKEN="$(qget "$f" DJAEGER_ACCESS_TOKEN)"
  [ -n "$TOKEN" ] || TOKEN="$(qget "$f" ACCESS_TOKEN)"
  [ -n "$URL" ] || URL="$(qget "$f" DJAEGER_RAILWAY_URL)"
  [ -n "$URL" ] || URL="$(qget "$f" ENDPOINT)"
done
[ -n "$TOKEN" ] || fail LEGACY_RAILWAY_TOKEN_NOT_FOUND
[ -n "$URL" ] || URL="$DEFAULT_URL"
case "$URL" in https://*) :;; *) fail INVALID_RAILWAY_URL;; esac

[ -r "$CFG" ] && cp -pf "$CFG" "$BACKUP/railway.env.pre" 2>/dev/null || true
setkv "$CFG" DJAEGER_ACCESS_TOKEN "$TOKEN" || fail WRITE_RAILWAY_TOKEN
setkv "$CFG" DJAEGER_RAILWAY_URL "$URL" || fail WRITE_RAILWAY_URL

IDENT="$ROOT/config/identity.env"
DID="$(qget "$IDENT" DEVICE_ID)"
[ -n "$DID" ] || DID="$(cat "$LEGACY/railway/device_id" 2>/dev/null | head -1 | tr -d '\r\n')"
[ -n "$DID" ] || DID="$(qget "$LEGACY/railway.conf" DEVICE_ID)"
[ -n "$DID" ] || DID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '\r\n')"
[ -n "$DID" ] || fail DEVICE_ID_CREATE_FAILED
[ -r "$IDENT" ] && cp -pf "$IDENT" "$BACKUP/identity.env.pre" 2>/dev/null || true
setkv "$IDENT" DEVICE_ID "$DID" || fail WRITE_DEVICE_ID

[ -r "$MOD/bin/remote_updater.sh" ] && cp -pf "$MOD/bin/remote_updater.sh" "$BACKUP/remote_updater.sh.pre" 2>/dev/null || true
cp -f "$ASSETS/remote_updater.sh" "$MOD/bin/remote_updater.sh.new.$$" || fail UPDATER_COPY_FAILED
chmod 755 "$MOD/bin/remote_updater.sh.new.$$"
mv -f "$MOD/bin/remote_updater.sh.new.$$" "$MOD/bin/remote_updater.sh" || fail UPDATER_INSTALL_FAILED
grep -Fq 'DJAEGER_ADAPTIVE_REMOTE_UPDATER_V2' "$MOD/bin/remote_updater.sh" || fail UPDATER_VERIFY_FAILED

if [ -r "$MOD/service.sh" ]; then
  cp -pf "$MOD/service.sh" "$BACKUP/service.sh.pre" 2>/dev/null || true
  if ! grep -Fq 'remote_updater.sh' "$MOD/service.sh" 2>/dev/null; then
    cat >>"$MOD/service.sh" <<'EOF'
# DJAEGER_ADAPTIVE_REMOTE_UPDATER_V2_BOOT
pkill -f "djaeger_ai_observer.*remote_updater.sh" 2>/dev/null || true
nohup sh "$MODDIR/bin/remote_updater.sh" "$ROOT" "$MODDIR" daemon >/dev/null 2>&1 &
EOF
  fi
  sh -n "$MOD/service.sh" >/dev/null 2>&1 || { cp -pf "$BACKUP/service.sh.pre" "$MOD/service.sh" 2>/dev/null; fail SERVICE_PATCH_SYNTAX; }
fi

kill_updaters
rm -f "$ROOT/runtime/remote_updater.pid" 2>/dev/null
sleep 1

# One synchronous live software-update transaction first.
sh "$MOD/bin/remote_updater.sh" "$ROOT" "$MOD" once >/dev/null 2>&1
ONCE_RC=$?

# Then leave exactly one persistent daemon.
kill_updaters
rm -f "$ROOT/runtime/remote_updater.pid" 2>/dev/null
nohup sh "$MOD/bin/remote_updater.sh" "$ROOT" "$MOD" daemon >/dev/null 2>&1 </dev/null &
sleep 2

# Keep the already-recovered telemetry bridge untouched; only verify it.
if [ -x "$MOD/bin/railway_bridge.sh" ]; then
  sh "$MOD/bin/railway_bridge.sh" "$ROOT" once >/dev/null 2>&1 || true
fi

RSTATE="$(qget "$ROOT/runtime/railway.env" RAILWAY_STATE)"
RHTTP="$(qget "$ROOT/runtime/railway.env" RAILWAY_HTTP)"
USTATE="$(qget "$ROOT/runtime/remote_update.env" STATE)"
USEQ="$(qget "$ROOT/runtime/remote_update.env" SEQ)"
UREL="$(qget "$ROOT/runtime/remote_update.env" RELEASE)"
UDETAIL="$(qget "$ROOT/runtime/remote_update.env" DETAIL)"
USCHEMA="$(qget "$ROOT/runtime/remote_update.env" SCHEMA)"
UPID="$(cat "$ROOT/runtime/remote_updater.pid" 2>/dev/null | head -1)"
ULIVE=NO
case "$UPID" in ''|*[!0-9]*) :;; *) kill -0 "$UPID" 2>/dev/null && ULIVE=YES;; esac

FINAL=PARTIAL
[ "$RHTTP" = 200 ] && [ "$ULIVE" = YES ] && case "$USTATE" in APPLIED|CURRENT) FINAL=PASS;; esac

{
  echo "RECOVERY_RESULT=$FINAL"
  echo "MODULE_VC=$VC"
  echo "DEVICE_ID_PRESENT=YES"
  echo "RAILWAY_CONFIG=RESTORED"
  echo "BRIDGE_STATE=${RSTATE:-UNKNOWN}"
  echo "BRIDGE_HTTP=${RHTTP:-NA}"
  echo "UPDATER_SCHEMA=${USCHEMA:-UNKNOWN}"
  echo "UPDATER_LIVE=$ULIVE"
  echo "UPDATER_STATE=${USTATE:-UNKNOWN}"
  echo "UPDATER_SEQ=${USEQ:-0}"
  echo "UPDATER_RELEASE=${UREL:-NONE}"
  echo "UPDATER_DETAIL=${UDETAIL:-NA}"
  echo "UPDATER_ONCE_RC=$ONCE_RC"
  echo "UPDATED_AT=$(date +%s)"
} >"$RESULT.tmp"
chmod 600 "$RESULT.tmp"; mv -f "$RESULT.tmp" "$RESULT"
cat "$RESULT"

[ "$FINAL" = PASS ] && exit 0
exit 2
