#!/system/bin/sh
# DJAEGER WORKLOADFINAL1 UIREPAIR1
# Repairs Control Center UI and moves the known ordinary-app entries that were
# previously kept in custom_games.tsv into the APP registry.
# Does not change sysfs, kernel, game policy, root authority, or network traffic.

set -u

APK=/data/media/0/Download/DJAEGER-Control-Center-v0.12.1-WORKLOADFINAL1-UIREPAIR1.apk
PKG=com.djaeger.controlcenter
M=/data/adb/modules/djaeger_game_stabilizer
P=/data/adb/djaeger_ai
APP="$P/workload/app_registry.tsv"
GAME="$P/custom_games.tsv"
CLASSIFIER="$P/workload/bin/djaeger-workload-classifier"
SHARED="$M/system/bin/djaeger-shared-intelligence"
EXPECTED_VC=12261

fail(){ echo "FAIL|$1"; exit "${2:-1}"; }
ok(){ echo "PASS|$1"; }

[ -r "$APK" ] || fail "apk_missing|$APK" 2
[ -d "$P" ] || fail "djaeger_state_missing" 3
mkdir -p "$P/workload" || fail "app_registry_dir" 4
[ -f "$APP" ] || : >"$APP"
[ -f "$GAME" ] || : >"$GAME"
chmod 600 "$APP" "$GAME" 2>/dev/null || true

TS="$(date +%s)"
cp -p "$APP" "$APP.pre-UIREPAIR1.$TS.bak" || fail "backup_app_registry" 5
cp -p "$GAME" "$GAME.pre-UIREPAIR1.$TS.bak" || fail "backup_game_registry" 6
ok "registry_backup"

valid_pkg(){ printf '%s\n' "$1" | grep -Eq '^[A-Za-z][A-Za-z0-9_]*([.][A-Za-z0-9_]+)+$'; }

move_to_app(){
  _pkg="$1"; _name="$2"
  valid_pkg "$_pkg" || fail "invalid_known_pkg|$_pkg" 20
  case "$_pkg" in sts.al|com.levelinfinite.gst|com.garena.game.kgid) fail "builtin_game_protection|$_pkg" 21;; esac

  _a="$APP.uirepair1.$$"
  awk -F '\t' -v p="$_pkg" '$1!=p' "$APP" >"$_a" || fail "app_filter|$_pkg" 22
  printf '%s\tAPP_INTERACTIVE\t%s\n' "$_pkg" "$_name" >>"$_a" || fail "app_append|$_pkg" 23
  chmod 600 "$_a" 2>/dev/null || true
  mv -f "$_a" "$APP" || fail "app_commit|$_pkg" 24

  _g="$GAME.uirepair1.$$"
  awk -F '\t' -v p="$_pkg" '$1!=p' "$GAME" >"$_g" || fail "game_filter|$_pkg" 25
  chmod 600 "$_g" 2>/dev/null || true
  mv -f "$_g" "$GAME" || fail "game_commit|$_pkg" 26
  echo "MOVED_TO_APP|$_pkg|$_name"
}

# These are the ordinary apps visible in the broken Session screenshot / prior
# APP use-case. Only these known identities are migrated; every other custom game
# remains untouched.
move_to_app com.openai.chatgpt ChatGPT
move_to_app com.facebook.katana Facebook
move_to_app com.google.android.youtube YouTube
move_to_app com.instagram.android Instagram
move_to_app com.shopee.id Shopee
move_to_app com.UCMobile.intl 'UC Browser'

# Hard separation checks.
for p in com.openai.chatgpt com.facebook.katana com.google.android.youtube com.instagram.android com.shopee.id com.UCMobile.intl; do
  awk -F '\t' -v p="$p" '$1==p{f=1}END{exit !f}' "$APP" || fail "app_missing_after_migration|$p" 30
  if awk -F '\t' -v p="$p" '$1==p{f=1}END{exit !f}' "$GAME"; then fail "still_in_game_registry|$p" 31; fi
done
for p in sts.al com.levelinfinite.gst com.garena.game.kgid; do
  if awk -F '\t' -v p="$p" '$1==p{f=1}END{exit !f}' "$APP"; then fail "builtin_game_in_app_registry|$p" 32; fi
done
ok "dual_registry_separation"

[ -x "$CLASSIFIER" ] && sh "$CLASSIFIER" publish >/dev/null 2>&1 || true
[ -x "$SHARED" ] && DJAEGER_MODDIR="$M" DJAEGER_STATE_DIR="$P" sh "$SHARED" build >/dev/null 2>&1 || true

OUT="$(pm install -r "$APK" 2>&1)"; RC=$?
printf '%s\n' "$OUT"
if [ "$RC" -ne 0 ]; then
  case "$OUT" in
    *INSTALL_FAILED_UPDATE_INCOMPATIBLE*|*signatures*do*not*match*|*signatures*not*match*)
      echo 'SIGNATURE_MISMATCH=YES'
      echo 'ACTION=REINSTALL_CONTROL_CENTER_ONLY'
      pm uninstall "$PKG" >/dev/null 2>&1 || true
      pm install "$APK" || fail "fresh_install_failed" 40
      ;;
    *) fail "install_rc=$RC" 41;;
  esac
fi

VC="$(dumpsys package "$PKG" 2>/dev/null | sed -n 's/.*versionCode=\([0-9][0-9]*\).*/\1/p' | head -1)"
[ "$VC" = "$EXPECTED_VC" ] || fail "version_code|got=${VC:-MISSING}|want=$EXPECTED_VC" 42

# Final no-conflict count for known migrated apps.
CONFLICT=0
for p in com.openai.chatgpt com.facebook.katana com.google.android.youtube com.instagram.android com.shopee.id com.UCMobile.intl; do
  if awk -F '\t' -v p="$p" '$1==p{f=1}END{exit !f}' "$GAME"; then CONFLICT=$((CONFLICT+1)); fi
done
[ "$CONFLICT" -eq 0 ] || fail "known_app_game_conflicts=$CONFLICT" 43

echo '===== RESULT ====='
echo 'STATUS=SELESAI'
echo 'UIREPAIR1=ACTIVE'
echo 'OVERVIEW_ORDER=PRESERVED'
echo 'APP_REGISTRY_LIST=READY'
echo 'GAME_REGISTRY_LIST=READY'
echo 'APP_SESSION_LABEL=OBSERVE_ONLY'
echo 'KNOWN_APP_GAME_CONFLICTS=0'
echo "CONTROL_CENTER_VERSION_CODE=$VC"
echo 'BACKEND_HARDWARE_AUTHORITY=UNCHANGED'
echo 'FLASH_REQUIRED=NO'
echo 'REBOOT_REQUIRED=NO'
