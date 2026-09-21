#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MODULE="$PROJECT_ROOT/observer-next/module"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT

run_ctl(){ DJAEGER_OBSERVER_ROOT="$TEST_ROOT" sh "$MODULE/bin/observerctl.sh" "$@"; }

LEGACY_ROOT="$TEST_ROOT/legacy_source"
LEGACY_MODULE_ROOT="$TEST_ROOT/legacy_module"
A=djaeger; B=work; C=hermes
FOREIGN_A="$LEGACY_ROOT/${A}_${B}"
FOREIGN_B="$LEGACY_ROOT/${C}_${B}"
mkdir -p "$LEGACY_ROOT/config" "$FOREIGN_A" "$FOREIGN_B" "$LEGACY_MODULE_ROOT/system/etc/djaeger/railway"

cat > "$LEGACY_ROOT/config/identity.env" <<'EOF'
DEVICE_ID=adaptive-migration-test
GEMINI_API_KEY=AIzaAdaptiveMigrationFakeKey1234567890
HERMES_ACCESS_KEY=hermes-clean-token-1234567890
HERMES_ENDPOINT=https://hermes.example.invalid
EOF
cat > "$LEGACY_MODULE_ROOT/system/etc/djaeger/railway/railway.conf" <<'EOF'
DJAEGER_ACCESS_TOKEN=railway-clean-token-1234567890
EOF
cat > "$FOREIGN_A/foreign.env" <<'EOF'
GEMINI_API_KEY=AIzaForeignProjectKeyMustNeverImport123456789
DEVICE_ID=foreign-device-must-never-import
EOF
cat > "$FOREIGN_B/foreign.env" <<'EOF'
HERMES_ACCESS_KEY=foreign-hermes-token-must-never-import
EOF
cat > "$LEGACY_ROOT/controller.sh" <<'EOF'
echo controller-must-not-be-imported
EOF

DJAEGER_LEGACY_ROOT="$LEGACY_ROOT" DJAEGER_LEGACY_MODULE_ROOT="$LEGACY_MODULE_ROOT" sh "$MODULE/bin/migrate.sh" "$TEST_ROOT" "$MODULE"
test -r "$TEST_ROOT/config/gemini_vault.env"
test -r "$TEST_ROOT/config/hermes_cloud.env"
test -r "$TEST_ROOT/config/identity.env"
test -r "$TEST_ROOT/config/railway.env"
test ! -e "$TEST_ROOT/recovery/legacy"
grep -Fqx 'KEY_1=AIzaAdaptiveMigrationFakeKey1234567890' "$TEST_ROOT/config/gemini_vault.env"
grep -Fqx 'HERMES_ACCESS_KEY=hermes-clean-token-1234567890' "$TEST_ROOT/config/hermes_cloud.env"
grep -Fqx 'DEVICE_ID=adaptive-migration-test' "$TEST_ROOT/config/identity.env"
grep -Fqx 'DJAEGER_ACCESS_TOKEN=railway-clean-token-1234567890' "$TEST_ROOT/config/railway.env"
! grep -R -F 'ForeignProjectKey' "$TEST_ROOT/config" "$TEST_ROOT/recovery"
! grep -R -F 'foreign-device-must-never-import' "$TEST_ROOT/config" "$TEST_ROOT/recovery"
grep -Fqx 'RAW_LEGACY_FILES_IMPORTED=0' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'FOREIGN_PROJECT_IMPORTS=0' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'MIGRATION_POLICY=EXPLICIT_KEY_ALLOWLIST_ONLY' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'LEGACY_HARDWARE_CONTROLLER_IMPORTED=NO' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'LEGACY_PROFILE_MAP_IMPORTED=NO' "$TEST_ROOT/recovery/migration.env"

printf 'com.example.game\nExample Game\n' | run_ctl game-registry-add-stdin >/dev/null
GAME_LIST=$(run_ctl game-registry-list)
grep -Fqx 'BUILTIN|sts.al|Arcane Legends' <<<"$GAME_LIST"
grep -Fqx 'MANUAL|com.example.game|Example Game' <<<"$GAME_LIST"

printf 'com.example.game\nExample App\n' | run_ctl app-registry-add-stdin >/dev/null
GAME_LIST=$(run_ctl game-registry-list)
APP_LIST=$(run_ctl app-registry-list)
! grep -Fq 'MANUAL|com.example.game|' <<<"$GAME_LIST"
grep -Fqx 'MANUAL|com.example.game|Example App' <<<"$APP_LIST"

run_ctl gemini-key-delete >/dev/null
FAKE_KEY='AIzaAdaptiveContractFakeKey1234567890'
printf '%s\n' "$FAKE_KEY" | run_ctl gemini-key-add-stdin >/dev/null
KEY_STATUS=$(run_ctl gemini-key-status)
grep -Fq 'KEY_CONFIGURED=YES' <<<"$KEY_STATUS"
grep -Fq 'KEY_COUNT=1' <<<"$KEY_STATUS"
! grep -Fq "$FAKE_KEY" <<<"$KEY_STATUS"

mkdir -p "$TEST_ROOT/runtime" "$TEST_ROOT/history" "$TEST_ROOT/policy" "$TEST_ROOT/recovery" "$TEST_ROOT/config"
NOW=$(date +%s)
cat > "$TEST_ROOT/runtime/snapshot.env" <<EOF
SCHEMA=DJAEGER_OBSERVER_V4
EPOCH=$NOW
ACTIVE_PACKAGE=sts.al
PACKAGE_SAMPLES=700
LITTLE_CUR_KHZ=1000000
BIG_CUR_KHZ=1800000
GPU_CUR_HZ=600000000
LITTLE_POLICY_PATH=/sys/devices/system/cpu/cpufreq/policy0
BIG_POLICY_PATH=/sys/devices/system/cpu/cpufreq/policy6
GPU_DEVFREQ_PATH=/sys/class/kgsl/kgsl-3d0/devfreq
LITTLE_AVAILABLE_KHZ=600000 1000000 1400000 1800000
BIG_AVAILABLE_KHZ=900000 1800000 2400000
GPU_AVAILABLE_HZ=300000000 600000000 900000000
CPU_TEMP_C=54.0
GPU_TEMP_C=50.0
SKIN_TEMP_C=39.0
BATTERY_TEMP_C=37.0
BATTERY_CURRENT_UA=-500000
BATTERY_VOLTAGE_UV=4200000
BATTERY_STATUS=Discharging
POWER_MW=2100
FRAME_EVIDENCE=VALID
FRAME_AT=$NOW
FPS_EST=60.0
JANK_PCT=1.0
P95_MS=17.0
P99_MS=20.0
EOF
cat > "$TEST_ROOT/runtime/frame.env" <<EOF
FRAME_EVIDENCE=VALID
FRAME_PACKAGE=sts.al
FRAME_AT=$NOW
FRAME_MS=16.67
FPS_EST=60.0
JANK_PCT=1.0
P95_MS=17.0
P99_MS=20.0
FRAME_N=120
EOF
cat > "$TEST_ROOT/history/learned_envelope.env" <<EOF
PACKAGE=sts.al
STATE=READY_HARDWARE_MODEL
SAMPLES=700
FRAME_WINDOWS=140
CONFIDENCE=90
FRAME_EVIDENCE=VALID
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
POWER_P50_MW=1800
POWER_P95_MW=2500
FPS_P50=60
JANK_P95=2
FRAME_P95_P95_MS=18
FRAME_P99_P95_MS=22
EOF
cat > "$TEST_ROOT/runtime/workload.env" <<EOF
AT=$NOW
PACKAGE=sts.al
WORKLOAD_CLASS=GAME
SOURCE=TEST
EOF
cat > "$TEST_ROOT/policy/candidate.env" <<EOF
SCHEMA=DJAEGER_ADAPTIVE_POLICY_V2
AT=$NOW
PACKAGE=sts.al
VERDICT=PROPOSED
CONFIDENCE=90
CANDIDATE_DIGEST=abc123
EXECUTOR_ENABLED=0
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF
cat > "$TEST_ROOT/runtime/shadow.env" <<EOF
SHADOW_STATE=PASS
CANDIDATE_DIGEST=abc123
SHADOW_WINDOWS=80
EOF
cat > "$TEST_ROOT/policy/approved.env" <<EOF
SCHEMA=DJAEGER_EXEC_APPROVAL_V1
AT=$NOW
EXPIRES_AT=$((NOW+180))
EXECUTOR_ALLOWED=YES
PACKAGE=sts.al
CANDIDATE_DIGEST=abc123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF
echo AUTO > "$TEST_ROOT/config/execution_mode"

FAKE="$TEST_ROOT/fakesys"
LP="$FAKE/sys/devices/system/cpu/cpufreq/policy0"
BP="$FAKE/sys/devices/system/cpu/cpufreq/policy6"
GP="$FAKE/sys/class/kgsl/kgsl-3d0/devfreq"
mkdir -p "$LP" "$BP" "$GP"
printf '600000\n' > "$LP/scaling_min_freq"; printf '1800000\n' > "$LP/scaling_max_freq"
printf '900000\n' > "$BP/scaling_min_freq"; printf '2400000\n' > "$BP/scaling_max_freq"
printf '300000000\n' > "$GP/min_freq"; printf '900000000\n' > "$GP/max_freq"
chmod 666 "$LP/"* "$BP/"* "$GP/"*

DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx '1400000' "$LP/scaling_max_freq"
grep -Fqx '1800000' "$BP/scaling_max_freq"
grep -Fqx '600000000' "$GP/max_freq"
grep -Fqx 'EXECUTOR_STATE=APPLIED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'READBACK=VERIFIED' "$TEST_ROOT/runtime/execution.env"

rm -f "$TEST_ROOT/policy/approved.env"
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx '1800000' "$LP/scaling_max_freq"
grep -Fqx '2400000' "$BP/scaling_max_freq"
grep -Fqx '900000000' "$GP/max_freq"
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"

# Re-apply the same approved candidate and prove active sysfs drift is detected.
cat > "$TEST_ROOT/policy/approved.env" <<EOF
SCHEMA=DJAEGER_EXEC_APPROVAL_V1
AT=$NOW
EXPIRES_AT=$((NOW+180))
EXECUTOR_ALLOWED=YES
PACKAGE=sts.al
CANDIDATE_DIGEST=abc123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
printf '1800000\n' > "$LP/scaling_max_freq"
if DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once; then
  echo "expected SYSFS drift reconciliation to return non-zero" >&2
  exit 1
fi
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=SYSFS_DRIFT' "$TEST_ROOT/runtime/execution.env"
test ! -e "$TEST_ROOT/runtime/execution_backup.env"

# Prove failed restore is fail-closed and preserves the recovery backup.
cat > "$TEST_ROOT/policy/approved.env" <<EOF
SCHEMA=DJAEGER_EXEC_APPROVAL_V1
AT=$NOW
EXPIRES_AT=$((NOW+180))
EXECUTOR_ALLOWED=YES
PACKAGE=sts.al
CANDIDATE_DIGEST=abc123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
rm -f "$TEST_ROOT/policy/approved.env"
chmod 444 "$GP/max_freq"
if DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once; then
  echo "expected failed restore to return non-zero" >&2
  exit 1
fi
grep -Fqx 'EXECUTOR_STATE=ROLLBACK_FAILED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'ROLLBACK_STATE=RESTORE_FAILED' "$TEST_ROOT/runtime/execution.env"
test -r "$TEST_ROOT/runtime/execution_backup.env"
grep -Fq ',ROLLBACK_FAILED,' "$TEST_ROOT/history/outcomes.csv"
chmod 666 "$GP/max_freq"
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once || true
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"
test ! -e "$TEST_ROOT/runtime/execution_backup.env"

cat > "$TEST_ROOT/recovery/migration.env" <<EOF
MIGRATION_STATE=CLEAN_IMPORT_CREATED
CREDENTIAL_FILE_COUNT=4
EOF

SYNC_OUT=$(run_ctl sync-request 105 DJAEGER_AI_ADAPTIVE_V2 contract-test-1)
grep -Fqx 'SYNC_STATUS=VERIFIED' <<<"$SYNC_OUT"
grep -Fqx 'PAIR_VERIFIED=YES' <<<"$SYNC_OUT"
SNAPSHOT="$TEST_ROOT/cc_snapshot"
grep -Fqx 'CONTRACT=DJAEGER_AI_ADAPTIVE_V2' "$SNAPSHOT"
grep -Fqx 'MODULE_VERSION_CODE=204' "$SNAPSHOT"
grep -Fqx 'CONTROL_CENTER_VERSION_CODE=105' "$SNAPSHOT"
grep -Fqx 'PAIR_VERIFIED=YES' "$SNAPSHOT"
grep -Fqx 'HANDSHAKE_SCHEMA=DJAEGER_AI_ADAPTIVE_V2' "$SNAPSHOT"
grep -Fq 'SNAPSHOT_GENERATION=' "$SNAPSHOT"
grep -Fqx 'WORKLOAD_CLASS=GAME' "$SNAPSHOT"
grep -Fqx 'SYSFS_WRITES=EXECUTOR_ONLY' "$SNAPSHOT"
grep -Fq 'EXECUTOR=ROLLED_BACK' "$SNAPSHOT"
grep -Fqx 'CLOUD_HARDWARE_AUTHORITY=NONE' "$SNAPSHOT"
grep -Fqx 'SHARED_INTELLIGENCE=MEASURED_DEVICE_CONTEXT_V2' "$SNAPSHOT"
grep -Fqx 'GEMINI_INTELLIGENCE_SCOPE=PROPOSE_DEVICE_BOUNDED' "$SNAPSHOT"
grep -Fqx 'HERMES_INTELLIGENCE_SCOPE=LOCAL_VALIDATE_PLUS_CLOUD_REVIEW' "$SNAPSHOT"
grep -Fqx 'SOURCE=LOCAL_EXECUTOR' "$SNAPSHOT"
grep -Fqx 'CONTEXT_PACKAGE=sts.al' "$SNAPSHOT"
grep -Fqx 'CONTEXT_CLASS=GAME' "$SNAPSHOT"
grep -Fq 'TEXT=Range adaptive sts.al dibatalkan' "$SNAPSHOT"
grep -Eq '^HARDWARE_OUTCOME_ROWS=[1-9][0-9]*
grep -Fq 'GEMINI_KEY_COUNT=1' <<<"$CRED"
grep -Fq 'HERMES_ACCESS_KEY_PRESENT=YES' <<<"$CRED"
! grep -Fq "$FAKE_KEY" <<<"$CRED"
! grep -Fq 'hermes-clean-token' <<<"$CRED"

echo 'module-contract-tests=PASS'
 "$SNAPSHOT"
grep -Fqx 'LAST_OUTCOME=ROLLED_BACK' "$SNAPSHOT"
! grep -Fq 'CPU/GPU, thermal, power, and frame behavior is being learned' "$SNAPSHOT"
grep -Fq 'WCLASS\" != GAME' "$MODULE/bin/frame_observer.sh"
grep -Fq 'WCLASS\" != APP' "$MODULE/bin/frame_observer.sh"

CRED=$(run_ctl credential-status)
grep -Fq 'GEMINI_KEY_COUNT=1' <<<"$CRED"
grep -Fq 'HERMES_ACCESS_KEY_PRESENT=YES' <<<"$CRED"
! grep -Fq "$FAKE_KEY" <<<"$CRED"
! grep -Fq 'hermes-clean-token' <<<"$CRED"

echo 'module-contract-tests=PASS'
