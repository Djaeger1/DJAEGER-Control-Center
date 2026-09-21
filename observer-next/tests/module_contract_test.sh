#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MODULE="$PROJECT_ROOT/observer-next/module"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT

run_ctl() {
  DJAEGER_OBSERVER_ROOT="$TEST_ROOT" sh "$MODULE/bin/observerctl.sh" "$@"
}

LEGACY_ROOT="$TEST_ROOT/legacy_source"
mkdir -p "$LEGACY_ROOT/config" "$LEGACY_ROOT/djaeger_work" "$LEGACY_ROOT/studio"
cat > "$LEGACY_ROOT/config/identity.env" <<'EOF'
DEVICE_ID=observer-migration-test
GEMINI_API_KEY=AIzaObserverMigrationFakeKey1234567890
HERMES_ACCESS_KEY=hermes-cleanroom-token-1234567890
HERMES_ENDPOINT=https://hermes.example.invalid
EOF
cat > "$LEGACY_ROOT/djaeger_work/foreign.env" <<'EOF'
GEMINI_API_KEY=AIzaForeignWorkKeyMustNeverImport123456789
HERMES_ACCESS_KEY=hermes-work-token-must-never-import
DEVICE_ID=work-device-must-never-import
EOF
cat > "$LEGACY_ROOT/studio/foreign.env" <<'EOF'
GEMINI_API_KEY=AIzaStudioKeyMustNeverImport1234567890123
EOF
cat > "$LEGACY_ROOT/controller.sh" <<'EOF'
echo legacy-controller-must-not-be-imported
EOF
DJAEGER_LEGACY_ROOT="$LEGACY_ROOT" sh "$MODULE/bin/migrate.sh" "$TEST_ROOT" "$MODULE"

test -r "$TEST_ROOT/config/gemini_vault.env"
test -r "$TEST_ROOT/config/hermes_cloud.env"
test -r "$TEST_ROOT/config/identity.env"
test ! -e "$TEST_ROOT/recovery/legacy"
grep -Fqx 'KEY_1=AIzaObserverMigrationFakeKey1234567890' "$TEST_ROOT/config/gemini_vault.env"
grep -Fqx 'HERMES_ACCESS_KEY=hermes-cleanroom-token-1234567890' "$TEST_ROOT/config/hermes_cloud.env"
grep -Fqx 'HERMES_ENDPOINT=https://hermes.example.invalid' "$TEST_ROOT/config/hermes_cloud.env"
grep -Fqx 'DEVICE_ID=observer-migration-test' "$TEST_ROOT/config/identity.env"
! grep -R -F 'ForeignWorkKey' "$TEST_ROOT/config" "$TEST_ROOT/recovery"
! grep -R -F 'work-device-must-never-import' "$TEST_ROOT/config" "$TEST_ROOT/recovery"
! grep -R -F 'StudioKeyMustNeverImport' "$TEST_ROOT/config" "$TEST_ROOT/recovery"
grep -Fqx 'RAW_LEGACY_FILES_IMPORTED=0' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'FOREIGN_PROJECT_IMPORTS=0' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'MIGRATION_POLICY=EXPLICIT_KEY_ALLOWLIST_ONLY' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'LEGACY_HARDWARE_CONTROLLER_IMPORTED=NO' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'LEGACY_PROFILE_MAP_IMPORTED=NO' "$TEST_ROOT/recovery/migration.env"

printf 'com.example.game\nExample Game\n' | run_ctl game-registry-add-stdin >/dev/null
GAME_LIST=$(run_ctl game-registry-list)
grep -Fqx 'BUILTIN|sts.al|Arcane Legends' <<<"$GAME_LIST"
grep -Fqx 'MANUAL|com.example.game|Example Game' <<<"$GAME_LIST"

# Moving the same package to APP must remove the GAME entry, keeping the
# registries mutually exclusive.
printf 'com.example.game\nExample App\n' | run_ctl app-registry-add-stdin >/dev/null
GAME_LIST=$(run_ctl game-registry-list)
APP_LIST=$(run_ctl app-registry-list)
! grep -Fq 'MANUAL|com.example.game|' <<<"$GAME_LIST"
grep -Fqx 'MANUAL|com.example.game|Example App' <<<"$APP_LIST"
if printf 'sts.al\nWrong Class\n' | run_ctl app-registry-add-stdin >/dev/null 2>&1; then
  echo 'built-in game was accepted as APP' >&2
  exit 1
fi

run_ctl gemini-key-delete >/dev/null
FAKE_KEY='AIzaObserverContractFakeKey1234567890'
printf '%s\n' "$FAKE_KEY" | run_ctl gemini-key-add-stdin >/dev/null
KEY_STATUS=$(run_ctl gemini-key-status)
grep -Fq 'KEY_CONFIGURED=YES' <<<"$KEY_STATUS"
grep -Fq 'KEY_COUNT=1' <<<"$KEY_STATUS"
! grep -Fq "$FAKE_KEY" <<<"$KEY_STATUS"

mkdir -p "$TEST_ROOT/runtime" "$TEST_ROOT/history" "$TEST_ROOT/policy" "$TEST_ROOT/recovery"
NOW=$(date +%s)
cat > "$TEST_ROOT/runtime/snapshot.env" <<EOF
SCHEMA=DJAEGER_OBSERVER_V3
EPOCH=$NOW
ACTIVE_PACKAGE=sts.al
PACKAGE_SAMPLES=700
LITTLE_CUR_KHZ=1000000
BIG_CUR_KHZ=1800000
GPU_CUR_HZ=600000000
LITTLE_AVAILABLE_KHZ=600000 1000000 1400000
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
CONFIDENCE=86
FRAME_EVIDENCE=VALID
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=2400000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=900000000
EOF
cat > "$TEST_ROOT/recovery/migration.env" <<EOF
MIGRATION_STATE=BACKUP_CREATED
CREDENTIAL_FILE_COUNT=2
EOF

# shellcheck disable=SC1090
. "$MODULE/bin/publisher.sh"
publish_cc "$TEST_ROOT"
SNAPSHOT="$TEST_ROOT/cc_snapshot"
grep -Fqx 'CONTRACT=OBSERVER_NEXT_V1' "$SNAPSHOT"
grep -Fqx 'MODULE_VERSION_CODE=201' "$SNAPSHOT"
grep -Fqx 'CONTROL_CENTER_VERSION_CODE=102' "$SNAPSHOT"
grep -Fqx 'WORKLOAD_CLASS=GAME' "$SNAPSHOT"
grep -Fqx 'SYSFS_WRITES=DISABLED' "$SNAPSHOT"
grep -Fqx 'EXECUTOR=NOT_STARTED' "$SNAPSHOT"
grep -Fqx 'HERMES_NEURON_USED_EST=UNAVAILABLE' "$SNAPSHOT"
grep -Fqx 'HERMES_NEURON_LIMIT=UNAVAILABLE' "$SNAPSHOT"

echo 'module-contract-tests=PASS'
