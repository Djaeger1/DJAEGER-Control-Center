#!/system/bin/sh
# DJAEGER NO-REBOOT RECOVERY2
# Scope: repair the dead Railway updater without network download, confirm Arcane
# GAME registration, hot-restart the controller only while no game session is bound,
# then refresh snapshot/audit/telemetry. No profile or core binary replacement.
M=/data/adb/modules/djaeger_game_stabilizer
P=/data/adb/djaeger_ai
R="$P/railway"
UP="$M/system/bin/djaeger-railway-updater"
GR="$M/system/bin/djaeger-game-registry"
AUD="$M/system/bin/djaeger-live-audit"
BR="$M/system/bin/djaeger-railway-bridge"
CFP="$M/system/bin/djaeger-cc-freshness-patch"
BUNDLED="${1:-}"

fail(){ echo "STATUS=FAIL"; echo "REASON=$1"; exit 1; }
proc_is(){
  _p="$1"; _n="$2"
  case "$_p" in ''|*[!0-9]*) return 1;; esac
  [ "$_p" -gt 1 ] 2>/dev/null && kill -0 "$_p" 2>/dev/null || return 1
  _c="$(tr '\000' ' ' <"/proc/$_p/cmdline" 2>/dev/null)"
  case "$_c" in *"$_n"*) return 0;; *) return 1;; esac
}

[ -d "$M" ] || fail MODULE_NOT_FOUND
VER="$(sed -n 's/^version=//p' "$M/module.prop" 2>/dev/null | head -1)"
case "$VER" in *VC129659*R89COMFORT2*) :;; *) fail "UNEXPECTED_MODULE=$VER";; esac
[ -r "$BUNDLED" ] || fail BUNDLED_UPDATER_MISSING
command -v sha256sum >/dev/null 2>&1 || fail SHA256SUM_MISSING
mkdir -p "$R" 2>/dev/null || fail RAILWAY_STATE_UNAVAILABLE
chmod 700 "$R" 2>/dev/null || true

# The updater is inside the signed APK. Validate the exact PID fix plus its own selftest.
grep -Fq '[ "$_old" != "$$" ]' "$BUNDLED" || fail BUNDLED_PID_GUARD_INVALID
grep -Fq '"$$" >"$PIDFILE"' "$BUNDLED" || fail BUNDLED_PID_WRITE_INVALID
DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$BUNDLED" selftest >/dev/null 2>&1 || fail BUNDLED_UPDATER_SELFTEST

BAK="$R/updater.pre_noreboot_recovery2"
[ -f "$UP" ] && cp -pf "$UP" "$BAK" 2>/dev/null || true
cp -f "$BUNDLED" "$UP.new.$$" 2>/dev/null && chmod 755 "$UP.new.$$" 2>/dev/null && mv -f "$UP.new.$$" "$UP" || fail UPDATER_INSTALL_FAILED
DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$UP" selftest >/dev/null 2>&1 || {
  [ -f "$BAK" ] && cp -pf "$BAK" "$UP" 2>/dev/null && chmod 755 "$UP" 2>/dev/null
  fail UPDATER_INSTALLED_SELFTEST
}

# Confirm Arcane belongs to GAME. Add only if it is genuinely absent.
[ -x "$GR" ] || fail GAME_REGISTRY_HELPER_MISSING
LIST="$(DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$GR" list 2>/dev/null)"
if ! printf '%s\n' "$LIST" | awk -F'|' '$2=="sts.al"{f=1} END{exit !f}'; then
  printf 'sts.al\nArcane Legends\n' | DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$GR" add-stdin >/dev/null 2>&1 || fail ARCANE_REGISTRY_REPAIR_FAILED
  LIST="$(DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$GR" list 2>/dev/null)"
fi
printf '%s\n' "$LIST" | awk -F'|' '$2=="sts.al"{f=1} END{exit !f}' || fail ARCANE_GAME_REGISTRY_MISSING

# Remove an accidental APP-registry conflict only if the file exists; keep a backup.
APPREG="$P/workload/app_registry.tsv"
if [ -r "$APPREG" ] && awk -F '\t' '$1=="sts.al"{f=1} END{exit !f}' "$APPREG" 2>/dev/null; then
  cp -pf "$APPREG" "$R/app_registry.pre_noreboot_recovery2.tsv" 2>/dev/null || fail APP_REGISTRY_BACKUP_FAILED
  awk -F '\t' '$1!="sts.al"' "$APPREG" >"$APPREG.tmp.$$" 2>/dev/null || fail APP_REGISTRY_FILTER_FAILED
  chmod 600 "$APPREG.tmp.$$" 2>/dev/null || true
  mv -f "$APPREG.tmp.$$" "$APPREG" || fail APP_REGISTRY_REWRITE_FAILED
fi
if [ -r "$APPREG" ] && awk -F '\t' '$1=="sts.al"{f=1} END{exit !f}' "$APPREG" 2>/dev/null; then fail ARCANE_STILL_IN_APP_REGISTRY; fi

# Revive updater daemon with process-identity validation.
OLDUP="$(cat "$R/updater.pid" 2>/dev/null)"
if proc_is "$OLDUP" djaeger-railway-updater; then kill "$OLDUP" 2>/dev/null || true; sleep 1; fi
rm -f "$R/updater.pid" 2>/dev/null
nohup sh "$UP" daemon >"$R/updater.recovery2.log" 2>&1 </dev/null &
_i=0; UP_LIVE=NO
while [ "$_i" -lt 12 ]; do
  NP="$(cat "$R/updater.pid" 2>/dev/null)"
  if proc_is "$NP" djaeger-railway-updater; then UP_LIVE=YES; break; fi
  sleep 1; _i=$((_i+1))
done
[ "$UP_LIVE" = YES ] || fail UPDATER_DAEMON_NOT_LIVE

# Refresh current controller process without touching controller.sh itself.
CTRL_ACTION=KEPT
if [ ! -s "$P/session_game" ]; then
  CP="$(cat "$P/controller.pid" 2>/dev/null)"
  if proc_is "$CP" djaeger_game_stabilizer/controller.sh; then
    kill "$CP" 2>/dev/null || true
    CTRL_ACTION=RESTART_REQUESTED
  fi
  SP="$(cat "$P/supervisor.pid" 2>/dev/null)"
  if ! proc_is "$SP" djaeger_game_stabilizer/supervisor.sh; then
    rm -f "$P/supervisor.pid" 2>/dev/null
    rm -rf "$P/supervisor.lock" 2>/dev/null
    nohup sh "$M/supervisor.sh" >"$M/supervisor.recovery2.log" 2>&1 </dev/null &
  fi
  _i=0
  while [ "$_i" -lt 20 ]; do
    NP="$(cat "$P/controller.pid" 2>/dev/null)"
    if proc_is "$NP" djaeger_game_stabilizer/controller.sh; then CTRL_ACTION=RESTARTED; break; fi
    sleep 1; _i=$((_i+1))
  done
  [ "$CTRL_ACTION" = RESTARTED ] || fail CONTROLLER_RESTART_FAILED
fi

# Refresh published UI/audit truth and send one bridge sample for remote verification.
sleep 2
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
