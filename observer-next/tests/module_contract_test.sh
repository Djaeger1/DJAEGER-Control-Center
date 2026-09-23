#!/usr/bin/env bash
set -euo pipefail
trap 'rc=$?; echo "CONTRACT_TEST_FAIL_LINE=$LINENO RC=$rc" >&2' ERR
PROJECT_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MODULE="$PROJECT_ROOT/observer-next/module"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT
run_ctl(){ DJAEGER_OBSERVER_ROOT="$TEST_ROOT" sh "$MODULE/bin/observerctl.sh" "$@"; }

# ---- Credential recovery contract ----
LEGACY_ROOT="$TEST_ROOT/legacy_source"
LEGACY_MODULE_ROOT="$TEST_ROOT/legacy_module"
A=djaeger; B=work; C=hermes
FOREIGN_A="$LEGACY_ROOT/${A}_${B}"
FOREIGN_B="$LEGACY_ROOT/${C}_${B}"
mkdir -p "$LEGACY_ROOT/hermes" "$LEGACY_ROOT/config" "$FOREIGN_A" "$FOREIGN_B"   "$LEGACY_MODULE_ROOT/system/etc/djaeger/railway"

cat > "$LEGACY_ROOT/config/identity.env" <<'EOF'
DEVICE_ID=adaptive-migration-test
EOF
cat > "$LEGACY_ROOT/gemini_keys.vault.pre-adaptive.bak" <<'EOF'
AIzaAdaptiveLegacyRawKey1111111111111111
AIzaAdaptiveLegacyRawKey2222222222222222
AIzaAdaptiveLegacyRawKey3333333333333333
AIzaAdaptiveLegacyRawKey4444444444444444
EOF
cat > "$LEGACY_ROOT/gemini.conf" <<'EOF'
GEMINI_API_KEY=AIzaAdaptiveLegacyRawKey3333333333333333
GEMINI_MODEL=gemini-3.6-flash
EOF
cat > "$LEGACY_ROOT/gemini_key_cooldowns" <<EOF
2|$(( $(date +%s) + 1800 ))|HTTP_429
EOF
cat > "$LEGACY_ROOT/hermes_cloud.conf.pre-adaptive.bak" <<'EOF'
HERMES_SHARED_TOKEN=hermes-legacy-shared-token-1234567890
ENDPOINT=https://hermes.example.invalid
EOF
cat > "$LEGACY_ROOT/HERMES_CLOUD_CREDENTIALS.txt" <<'EOF'
HERMES_ENDPOINT=/v1/chat
HERMES_CLOUD_ID=hermes-cloud-test-id
EOF
cat > "$LEGACY_ROOT/hermes/neuron_budget.env" <<EOF
EPOCH_DAY=$(( $(date +%s) / 86400 ))
USED_EST=4321
FAST_CALLS=9
SMART_CALLS=2
DEEP_CALLS=1
LIMIT=10000
EOF
cat > "$LEGACY_MODULE_ROOT/system/etc/djaeger/railway/railway.conf" <<'EOF'
DJAEGER_ACCESS_TOKEN=railway-clean-token-1234567890
DJAEGER_RAILWAY_URL=https://djaeger.example.invalid
EOF
cat > "$FOREIGN_A/foreign.env" <<'EOF'
GEMINI_API_KEY=AIzaForeignProjectKeyMustNeverImport123456789
DEVICE_ID=foreign-device-must-never-import
EOF
cat > "$FOREIGN_B/foreign.env" <<'EOF'
HERMES_ACCESS_KEY=foreign-hermes-token-must-never-import
EOF

DJAEGER_LEGACY_ROOT="$LEGACY_ROOT" DJAEGER_LEGACY_MODULE_ROOT="$LEGACY_MODULE_ROOT"   sh "$MODULE/bin/migrate.sh" "$TEST_ROOT" "$MODULE"

grep -Fqx 'KEY_1=AIzaAdaptiveLegacyRawKey1111111111111111' "$TEST_ROOT/config/gemini_vault.env"
grep -Fqx 'KEY_2=AIzaAdaptiveLegacyRawKey2222222222222222' "$TEST_ROOT/config/gemini_vault.env"
grep -Fqx 'KEY_3=AIzaAdaptiveLegacyRawKey3333333333333333' "$TEST_ROOT/config/gemini_vault.env"
grep -Fqx 'KEY_4=AIzaAdaptiveLegacyRawKey4444444444444444' "$TEST_ROOT/config/gemini_vault.env"
grep -Fqx '3' "$TEST_ROOT/config/gemini_slot"
grep -Eq '^KEY_2_UNTIL=[0-9]+$' "$TEST_ROOT/config/gemini_cooldown.env"
grep -Fqx 'HERMES_ACCESS_KEY=hermes-legacy-shared-token-1234567890' "$TEST_ROOT/config/hermes_cloud.env"
grep -Fqx 'HERMES_ENDPOINT=https://hermes.example.invalid/v1/chat' "$TEST_ROOT/config/hermes_cloud.env"
grep -Fqx 'HERMES_CLOUD_ID=hermes-cloud-test-id' "$TEST_ROOT/config/hermes_cloud.env"
grep -Fqx 'USED_EST=4321' "$TEST_ROOT/config/hermes_neuron_legacy.env"
grep -Fqx 'LIMIT=10000' "$TEST_ROOT/config/hermes_neuron_legacy.env"
grep -Fqx 'DEVICE_ID=adaptive-migration-test' "$TEST_ROOT/config/identity.env"
grep -Fqx 'DJAEGER_ACCESS_TOKEN=railway-clean-token-1234567890' "$TEST_ROOT/config/railway.env"
grep -Fqx 'DJAEGER_RAILWAY_URL=https://djaeger.example.invalid' "$TEST_ROOT/config/railway.env"
! grep -R -F 'ForeignProjectKey' "$TEST_ROOT/config" "$TEST_ROOT/recovery"
! grep -R -F 'foreign-device-must-never-import' "$TEST_ROOT/config" "$TEST_ROOT/recovery"
grep -Fqx 'MIGRATION_SCHEMA=9' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'MIGRATION_STATE=RECOVERED' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'RAW_GEMINI_VAULT_FOUND=YES' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'GEMINI_COOLDOWN_FOUND=YES' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'GEMINI_KEY_COUNT=4' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'HERMES_ACCESS_KEY_PRESENT=YES' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'HERMES_ENDPOINT_PRESENT=YES' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'HERMES_CLOUD_ID_PRESENT=YES' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'NEURON_LOCAL_ESTIMATE_PRESENT=YES' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'RAW_LEGACY_FILES_IMPORTED=0' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'FOREIGN_PROJECT_IMPORTS=0' "$TEST_ROOT/recovery/migration.env"
grep -Fqx 'MIGRATION_POLICY=EXPLICIT_KEY_ALLOWLIST_ONLY' "$TEST_ROOT/recovery/migration.env"

CRED=$(run_ctl credential-status)
grep -Fqx 'GEMINI_KEY_COUNT=4' <<<"$CRED"
grep -Fqx 'GEMINI_READY_COUNT=3' <<<"$CRED"
grep -Fqx 'GEMINI_COOLDOWN_COUNT=1' <<<"$CRED"
grep -Fqx 'HERMES_ACCESS_KEY_PRESENT=YES' <<<"$CRED"
grep -Fqx 'HERMES_ENDPOINT_PRESENT=YES' <<<"$CRED"
grep -Fqx 'HERMES_CLOUD_ID_PRESENT=YES' <<<"$CRED"
! grep -Fq 'AIzaAdaptiveLegacyRawKey' <<<"$CRED"
! grep -Fq 'hermes-legacy-shared-token' <<<"$CRED"

# ---- Registry contract ----
printf 'com.example.game\nExample Game\n' | run_ctl game-registry-add-stdin >/dev/null
grep -Fqx 'MANUAL|com.example.game|Example Game' <<<"$(run_ctl game-registry-list)"
printf 'com.example.game\nExample App\n' | run_ctl app-registry-add-stdin >/dev/null
! grep -Fq 'MANUAL|com.example.game|' <<<"$(run_ctl game-registry-list)"
grep -Fqx 'MANUAL|com.example.game|Example App' <<<"$(run_ctl app-registry-list)"

# ---- Runtime / executor contract ----
mkdir -p "$TEST_ROOT/runtime" "$TEST_ROOT/history" "$TEST_ROOT/policy" "$TEST_ROOT/config"
NOW=$(date +%s)
cat > "$TEST_ROOT/runtime/snapshot.env" <<EOF
SCHEMA=DJAEGER_OBSERVER_V4
EPOCH=$NOW
SAMPLE_SEQ=700
ACTIVE_PACKAGE=sts.al
TOP_PACKAGE=sts.al
PACKAGE_SOURCE=FOREGROUND
VISIBLE_GAME=sts.al
PACKAGE_SAMPLES=700
LEARNING_STATE=READY_HARDWARE_MODEL
LITTLE_CUR_KHZ=1000000
BIG_CUR_KHZ=1800000
GPU_CUR_HZ=600000000
LITTLE_POLICY_PATH=/sys/devices/system/cpu/cpufreq/policy0
BIG_POLICY_PATH=/sys/devices/system/cpu/cpufreq/policy6
GPU_DEVFREQ_PATH=/sys/class/kgsl/kgsl-3d0/devfreq
LITTLE_AVAILABLE_KHZ=600000 1000000 1400000 1800000
BIG_AVAILABLE_KHZ=900000 1800000 2400000
GPU_AVAILABLE_HZ=300000000 600000000 900000000
CPU_TEMP_C=54
GPU_TEMP_C=50
SKIN_TEMP_C=39
BATTERY_TEMP_C=37
BATTERY_CURRENT_UA=-500000
BATTERY_VOLTAGE_UV=4200000
BATTERY_STATUS=Discharging
POWER_MW=2100
FRAME_EVIDENCE=VALID
FRAME_AT=$NOW
FPS_EST=60
JANK_PCT=1
P95_MS=17
P99_MS=20
EOF
cat > "$TEST_ROOT/runtime/frame.env" <<EOF
FRAME_EVIDENCE=VALID
FRAME_PACKAGE=sts.al
FRAME_AT=$NOW
FRAME_MS=16.67
FPS_EST=60
JANK_PCT=1
P95_MS=17
P99_MS=20
FRAME_N=120
EOF
cat > "$TEST_ROOT/history/learned_envelope.env" <<EOF
PACKAGE=sts.al
STATE=READY_HARDWARE_MODEL
SAMPLES=700
FRAME_WINDOWS=140
CONFIDENCE=90
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
POWER_P50_MW=2200
POWER_P95_MW=3200
FPS_P50=60
JANK_P95=2
FRAME_P95_P95_MS=18
FRAME_P99_P95_MS=22
OUTCOME_ROWS=0
KEEP_ROWS=0
ROLLBACK_ROWS=0
OUTCOME_FEEDBACK=NONE
EOF
cat > "$TEST_ROOT/runtime/workload.env" <<EOF
AT=$NOW
PACKAGE=sts.al
WORKLOAD_CLASS=GAME
SOURCE=TEST
EOF
cat > "$TEST_ROOT/runtime/network.env" <<EOF
SESSION_ACTIVE=1
PACKAGE=sts.al
PROBE_TARGET=1.1.1.1
PING_CURRENT_MS=22.0
PING_AVG_MS=24.0
PING_P95_MS=30.0
JITTER_MS=3.0
PACKET_LOSS_PCT=0
QUALITY=GOOD
SOURCE=READ_ONLY_ICMP_PROBE
UPDATED_AT=$NOW
EOF
cat > "$TEST_ROOT/config/hermes_neuron_live.env" <<EOF
SCHEMA=DJAEGER_NEURON_LIVE_V1
UTC_DAY=$(date -u +%Y-%m-%d)
RESET_AT=00:00_UTC
RESET_AT_WIB=07:00
USED_EST=0
LIMIT=10000
FAST_CALLS=0
SMART_CALLS=0
DEEP_CALLS=0
SUCCESS_CALLS=0
LAST_DELTA=0
METHOD=INITIALIZED
ESTIMATED=YES
SOURCE=LIVE_SUCCESSFUL_HERMES_CLOUD_ONLY
UPDATED_AT=$NOW
EOF
cat > "$TEST_ROOT/runtime/consensus.env" <<EOF
CONSENSUS_STATE=PENDING_SHADOW
UPDATED_AT=$NOW
EOF
cat > "$TEST_ROOT/runtime/shadow.env" <<EOF
SHADOW_STATE=PASS
CANDIDATE_DIGEST=abc123
SHADOW_WINDOWS=80
UPDATED_AT=$NOW
EOF
cat > "$TEST_ROOT/policy/candidate.env" <<EOF
SCHEMA=DJAEGER_ADAPTIVE_POLICY_V2
AT=$NOW
PACKAGE=sts.al
CONFIDENCE=90
INTENT=FRAME_FIRST_BALANCED
CANDIDATE_DIGEST=abc123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF
cat > "$TEST_ROOT/policy/approved.env" <<EOF
SCHEMA=DJAEGER_EXEC_APPROVAL_V2
AT=$NOW
EXPIRES_AT=$((NOW+180))
EXECUTOR_ALLOWED=YES
PACKAGE=sts.al
INTENT=FRAME_FIRST_BALANCED
ACTUATORS=ALL
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
grep -Fqx 'EXECUTOR_STATE=APPLIED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'READBACK=VERIFIED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx '1400000' "$LP/scaling_max_freq"
grep -Fqx '1800000' "$BP/scaling_max_freq"
grep -Fqx '600000000' "$GP/max_freq"

# Approval churn must NOT abort a just-applied trial. The active digest is
# pinned until outcome evidence exists; only device-truth safety can end it.
rm -f "$TEST_ROOT/policy/approved.env"
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx 'EXECUTOR_STATE=APPLIED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=ACTIVE_TRIAL_PINNED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx '1400000' "$LP/scaling_max_freq"
grep -Fqx '1800000' "$BP/scaling_max_freq"
grep -Fqx '600000000' "$GP/max_freq"

# Leaving the game is a real safety/context boundary and must restore now.
cat > "$TEST_ROOT/runtime/workload.env" <<EOF
AT=$NOW
PACKAGE=sts.al
WORKLOAD_CLASS=APP
SOURCE=TEST
EOF
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once || true
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=NON_GAME' "$TEST_ROOT/runtime/execution.env"
grep -Fqx '1800000' "$LP/scaling_max_freq"
grep -Fqx '2400000' "$BP/scaling_max_freq"
grep -Fqx '900000000' "$GP/max_freq"
cat > "$TEST_ROOT/runtime/workload.env" <<EOF
AT=$NOW
PACKAGE=sts.al
WORKLOAD_CLASS=GAME
SOURCE=TEST
EOF

# GPU-only ownership: CPU policies must remain byte-for-byte untouched while
# the candidate trims only GPU. Rollback must likewise touch only GPU.
cat > "$TEST_ROOT/runtime/shadow.env" <<EOF
SHADOW_STATE=PASS
CANDIDATE_DIGEST=gpuonly123
SHADOW_WINDOWS=80
UPDATED_AT=$NOW
EOF
cat > "$TEST_ROOT/policy/candidate.env" <<EOF
SCHEMA=DJAEGER_ADAPTIVE_POLICY_V3
AT=$NOW
PACKAGE=sts.al
CONFIDENCE=90
INTENT=POWER_EFFICIENCY
ACTUATORS=GPU
CANDIDATE_DIGEST=gpuonly123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF
cat > "$TEST_ROOT/policy/approved.env" <<EOF
SCHEMA=DJAEGER_EXEC_APPROVAL_V2
AT=$NOW
EXPIRES_AT=$((NOW+180))
EXECUTOR_ALLOWED=YES
PACKAGE=sts.al
INTENT=POWER_EFFICIENCY
ACTUATORS=GPU
CANDIDATE_DIGEST=gpuonly123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF
LP_MIN_BEFORE=$(cat "$LP/scaling_min_freq"); LP_MAX_BEFORE=$(cat "$LP/scaling_max_freq")
BP_MIN_BEFORE=$(cat "$BP/scaling_min_freq"); BP_MAX_BEFORE=$(cat "$BP/scaling_max_freq")
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx 'EXECUTOR_STATE=APPLIED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'APPLIED_ACTUATORS=GPU' "$TEST_ROOT/runtime/execution.env"
grep -Fqx "$LP_MIN_BEFORE" "$LP/scaling_min_freq"
grep -Fqx "$LP_MAX_BEFORE" "$LP/scaling_max_freq"
grep -Fqx "$BP_MIN_BEFORE" "$BP/scaling_min_freq"
grep -Fqx "$BP_MAX_BEFORE" "$BP/scaling_max_freq"
grep -Fqx '600000000' "$GP/max_freq"

rm -f "$TEST_ROOT/policy/approved.env"
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx 'EXECUTOR_STATE=APPLIED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=ACTIVE_TRIAL_PINNED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx "$LP_MIN_BEFORE" "$LP/scaling_min_freq"
grep -Fqx "$LP_MAX_BEFORE" "$LP/scaling_max_freq"
grep -Fqx "$BP_MIN_BEFORE" "$BP/scaling_min_freq"
grep -Fqx "$BP_MAX_BEFORE" "$BP/scaling_max_freq"
grep -Fqx '600000000' "$GP/max_freq"

# Force a real context exit; GPU rollback must not write either CPU policy.
cat > "$TEST_ROOT/runtime/workload.env" <<EOF
AT=$NOW
PACKAGE=sts.al
WORKLOAD_CLASS=APP
SOURCE=TEST
EOF
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once || true
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"
grep -Fqx "$LP_MIN_BEFORE" "$LP/scaling_min_freq"
grep -Fqx "$LP_MAX_BEFORE" "$LP/scaling_max_freq"
grep -Fqx "$BP_MIN_BEFORE" "$BP/scaling_min_freq"
grep -Fqx "$BP_MAX_BEFORE" "$BP/scaling_max_freq"
grep -Fqx '900000000' "$GP/max_freq"
cat > "$TEST_ROOT/runtime/workload.env" <<EOF
AT=$NOW
PACKAGE=sts.al
WORKLOAD_CLASS=GAME
SOURCE=TEST
EOF

# Qualcomm/MIUI may legitimately relax a raised LITTLE min_freq back toward
# the pre-transaction floor while preserving the exact max_freq. That bounded
# power-saving relaxation must not be misclassified as external ownership loss.
cat > "$TEST_ROOT/runtime/shadow.env" <<EOF
SHADOW_STATE=PASS
CANDIDATE_DIGEST=nativerelax123
SHADOW_WINDOWS=80
UPDATED_AT=$NOW
EOF
cat > "$TEST_ROOT/policy/candidate.env" <<EOF
SCHEMA=DJAEGER_ADAPTIVE_POLICY_V3
AT=$NOW
PACKAGE=sts.al
CONFIDENCE=90
INTENT=FRAME_FIRST_BALANCED
ACTUATORS=ALL
CANDIDATE_DIGEST=nativerelax123
LITTLE_MIN_KHZ=1000000
LITTLE_MAX_KHZ=1800000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=2400000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=900000000
EOF
cat > "$TEST_ROOT/policy/approved.env" <<EOF
SCHEMA=DJAEGER_EXEC_APPROVAL_V2
AT=$NOW
EXPIRES_AT=$((NOW+180))
EXECUTOR_ALLOWED=YES
PACKAGE=sts.al
INTENT=FRAME_FIRST_BALANCED
ACTUATORS=ALL
CANDIDATE_DIGEST=nativerelax123
LITTLE_MIN_KHZ=1000000
LITTLE_MAX_KHZ=1800000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=2400000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=900000000
EOF
rm -f "$TEST_ROOT/runtime/execution_suppress.env"
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx 'EXECUTOR_STATE=APPLIED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'APPLIED_LITTLE=1000000-1800000' "$TEST_ROOT/runtime/execution.env"
printf '600000\n' > "$LP/scaling_min_freq"
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx 'EXECUTOR_STATE=APPLIED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=ACTIVE_TRIAL_PINNED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'READBACK=NATIVE_RELAXED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx '600000' "$LP/scaling_min_freq"
test ! -e "$TEST_ROOT/runtime/execution_suppress.env"
! grep -Fq 'nativerelax123,RELEASED,SYSFS_EXTERNAL_OVERRIDE' "$TEST_ROOT/history/outcomes.csv"

# Exit the test transaction through the normal safety boundary and prove the
# original backup is restored before the strict drift regression continues.
cat > "$TEST_ROOT/runtime/workload.env" <<EOF
AT=$NOW
PACKAGE=sts.al
WORKLOAD_CLASS=APP
SOURCE=TEST
EOF
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once || true
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"
grep -Fqx '600000' "$LP/scaling_min_freq"
grep -Fqx '1800000' "$LP/scaling_max_freq"
cat > "$TEST_ROOT/runtime/workload.env" <<EOF
AT=$NOW
PACKAGE=sts.al
WORKLOAD_CLASS=GAME
SOURCE=TEST
EOF

# Restore full-policy fixture for the existing drift regression.
cat > "$TEST_ROOT/runtime/shadow.env" <<EOF
SHADOW_STATE=PASS
CANDIDATE_DIGEST=abc123
SHADOW_WINDOWS=80
UPDATED_AT=$NOW
EOF
cat > "$TEST_ROOT/policy/candidate.env" <<EOF
SCHEMA=DJAEGER_ADAPTIVE_POLICY_V3
AT=$NOW
PACKAGE=sts.al
CONFIDENCE=90
INTENT=FRAME_FIRST_BALANCED
ACTUATORS=ALL
CANDIDATE_DIGEST=abc123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF

# Re-apply and prove a later external SYSFS override is not fought.
# Once a verified transaction is changed by another kernel/vendor owner,
# DJAEGER relinquishes ownership and leaves the external value untouched.
cat > "$TEST_ROOT/policy/approved.env" <<EOF
SCHEMA=DJAEGER_EXEC_APPROVAL_V2
AT=$NOW
EXPIRES_AT=$((NOW+180))
EXECUTOR_ALLOWED=YES
PACKAGE=sts.al
INTENT=FRAME_FIRST_BALANCED
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
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once || true
grep -Fqx 'EXECUTOR_STATE=IDLE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=SYSFS_EXTERNAL_OVERRIDE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'READBACK=EXTERNAL_OVERRIDE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'ROLLBACK_STATE=RELINQUISHED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx '1800000' "$LP/scaling_max_freq"
grep -Fqx '2400000' "$BP/scaling_max_freq"
grep -Fqx '900000000' "$GP/max_freq"
test ! -e "$TEST_ROOT/runtime/execution_backup.env"
grep -Fq ',RELEASED,SYSFS_EXTERNAL_OVERRIDE,' "$TEST_ROOT/history/outcomes.csv"
grep -Fqx 'DIGEST=abc123' "$TEST_ROOT/runtime/execution_suppress.env"

# The exact same digest must not immediately re-apply after native override.
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once || true
grep -Fqx 'EXECUTOR_STATE=IDLE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=RECENT_EXTERNAL_OVERRIDE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx '1800000' "$LP/scaling_max_freq"
grep -Fqx '2400000' "$BP/scaling_max_freq"
grep -Fqx '900000000' "$GP/max_freq"

# Transaction-aware cleanup regression: BIG is already externally owned
# while LITTLE still equals the DJAEGER-applied value. Make LITTLE unwritable
# so its single restore attempt loses; cleanup must relinquish rather than
# hard-latch merely because LITTLE still reads as APPLIED.
rm -f "$TEST_ROOT/runtime/execution_suppress.env"
printf '600000\n' > "$LP/scaling_min_freq"; printf '1800000\n' > "$LP/scaling_max_freq"
printf '900000\n' > "$BP/scaling_min_freq"; printf '2400000\n' > "$BP/scaling_max_freq"
printf '300000000\n' > "$GP/min_freq"; printf '900000000\n' > "$GP/max_freq"
chmod 666 "$LP/"* "$BP/"* "$GP/"*

cat > "$TEST_ROOT/runtime/shadow.env" <<EOF
SHADOW_STATE=PASS
CANDIDATE_DIGEST=cleanuporder123
SHADOW_WINDOWS=80
UPDATED_AT=$NOW
EOF
cat > "$TEST_ROOT/policy/candidate.env" <<EOF
SCHEMA=DJAEGER_ADAPTIVE_POLICY_V3
AT=$NOW
PACKAGE=sts.al
CONFIDENCE=90
INTENT=FRAME_FIRST_BALANCED
ACTUATORS=ALL
CANDIDATE_DIGEST=cleanuporder123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF
cat > "$TEST_ROOT/policy/approved.env" <<EOF
SCHEMA=DJAEGER_EXEC_APPROVAL_V2
AT=$NOW
EXPIRES_AT=$((NOW+180))
EXECUTOR_ALLOWED=YES
PACKAGE=sts.al
INTENT=FRAME_FIRST_BALANCED
ACTUATORS=ALL
CANDIDATE_DIGEST=cleanuporder123
LITTLE_MIN_KHZ=600000
LITTLE_MAX_KHZ=1400000
BIG_MIN_KHZ=900000
BIG_MAX_KHZ=1800000
GPU_MIN_HZ=300000000
GPU_MAX_HZ=600000000
EOF

DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx 'EXECUTOR_STATE=APPLIED' "$TEST_ROOT/runtime/execution.env"
chmod 444 "$LP/scaling_min_freq" "$LP/scaling_max_freq"
printf '2000000\n' > "$BP/scaling_max_freq"
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once || true

grep -Fqx 'EXECUTOR_STATE=IDLE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=SYSFS_EXTERNAL_OVERRIDE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'ROLLBACK_STATE=RELINQUISHED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'LITTLE_PRE_STATE=APPLIED' "$TEST_ROOT/runtime/execution_restore.env"
grep -Fqx 'LITTLE_STATUS=RELINQUISHED_APPLIED_AFTER_EXTERNAL_RACE' "$TEST_ROOT/runtime/execution_restore.env"
grep -Fqx 'BIG_PRE_STATE=EXTERNAL' "$TEST_ROOT/runtime/execution_restore.env"
grep -Fqx 'BIG_STATUS=RELINQUISHED' "$TEST_ROOT/runtime/execution_restore.env"
! grep -Fq 'cleanuporder123,ROLLBACK_FAILED,SYSFS_EXTERNAL_OVERRIDE_CLEANUP' "$TEST_ROOT/history/outcomes.csv"
grep -Fq 'cleanuporder123,RELEASED,SYSFS_EXTERNAL_OVERRIDE' "$TEST_ROOT/history/outcomes.csv"
test ! -e "$TEST_ROOT/runtime/execution_backup.env"

chmod 666 "$LP/scaling_min_freq" "$LP/scaling_max_freq"
printf '600000\n' > "$LP/scaling_min_freq"; printf '1800000\n' > "$LP/scaling_max_freq"
printf '900000\n' > "$BP/scaling_min_freq"; printf '2400000\n' > "$BP/scaling_max_freq"
printf '300000000\n' > "$GP/min_freq"; printf '900000000\n' > "$GP/max_freq"
rm -f "$TEST_ROOT/runtime/execution_suppress.env"

# Simulate a legacy latched SYSFS-drift restore failure from a previous runtime.
# Explicit relinquish must clear the stale backup WITHOUT writing old values.
printf '700000000\n' > "$GP/max_freq"
cat > "$TEST_ROOT/runtime/execution_backup.env" <<EOF
AT=$NOW
DIGEST=legacydrift123
PACKAGE=sts.al
INTENT=POWER_EFFICIENCY
ACTUATORS=GPU
LITTLE_PATH=/sys/devices/system/cpu/cpufreq/policy0
LITTLE_MIN=600000
LITTLE_MAX=1800000
BIG_PATH=/sys/devices/system/cpu/cpufreq/policy6
BIG_MIN=900000
BIG_MAX=2400000
GPU_PATH=/sys/class/kgsl/kgsl-3d0/devfreq
GPU_MIN=300000000
GPU_MAX=900000000
EOF
cat > "$TEST_ROOT/runtime/execution.env" <<EOF
EXECUTOR_STATE=ROLLBACK_FAILED
EXECUTOR_REASON=RESTORE_FAILURE_LATCHED
ACTIVE_DIGEST=legacydrift123
APPLIED_PACKAGE=sts.al
APPLIED_INTENT=POWER_EFFICIENCY
APPLIED_ACTUATORS=GPU
APPLIED_LITTLE=600000-1800000
APPLIED_BIG=900000-2400000
APPLIED_GPU=300000000-600000000
READBACK=RESTORE_FAILED
ROLLBACK_STATE=RESTORE_FAILED
APPLIED_AT=$NOW
MONITOR_BAD_COUNT=0
MONITOR_SAMPLES=0
UPDATED_AT=$NOW
EOF
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" resolve-latched
echo "=== RESOLVE-LATCHED STATE ==="
cat "$TEST_ROOT/runtime/execution.env" || true
echo "=== RESOLVE-LATCHED RESTORE ==="
cat "$TEST_ROOT/runtime/execution_restore.env" || true
echo "=== RESOLVE-LATCHED OUTCOMES ==="
tail -n 5 "$TEST_ROOT/history/outcomes.csv" || true
grep -Fqx '700000000' "$GP/max_freq"
test ! -e "$TEST_ROOT/runtime/execution_backup.env"
grep -Fqx 'EXECUTOR_STATE=IDLE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=LATCHED_RECHECK_RESOLVED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'ROLLBACK_STATE=RELINQUISHED' "$TEST_ROOT/runtime/execution.env"
grep -Fq ',RELEASED,LATCHED_RECHECK_EXTERNAL_OVERRIDE,' "$TEST_ROOT/history/outcomes.csv"

# Legacy partial-apply latch: state lost digest/targets, but the ledger still
# contains the failed digest and an earlier verified row with exact targets.
# Resolver must reconstruct identity read-only and supersede the correct digest.
printf '500000\n' > "$LP/scaling_min_freq"; printf '1700000\n' > "$LP/scaling_max_freq"
printf '800000\n' > "$BP/scaling_min_freq"; printf '2200000\n' > "$BP/scaling_max_freq"
printf '300000000\n' > "$GP/min_freq"; printf '900000000\n' > "$GP/max_freq"

cat >> "$TEST_ROOT/history/outcomes.csv" <<EOF
$NOW,sts.al,legacypartial123,APPLIED_VERIFIED,CONSENSUS_SHADOW_APPROVED,60,1,17,2100,VERIFIED,600000-1400000,900000-1800000,300000000-600000000
$((NOW+1)),sts.al,legacypartial123,ROLLBACK_FAILED,APPLY_OR_READBACK_FAILED,60,1,17,2100,RESTORE_FAILED,NA,NA,NA
EOF

cat > "$TEST_ROOT/runtime/execution_backup.env" <<EOF
ACTUATORS=ALL
LITTLE_PATH=/sys/devices/system/cpu/cpufreq/policy0
LITTLE_MIN=600000
LITTLE_MAX=1800000
BIG_PATH=/sys/devices/system/cpu/cpufreq/policy6
BIG_MIN=900000
BIG_MAX=2400000
GPU_PATH=/sys/class/kgsl/kgsl-3d0/devfreq
GPU_MIN=300000000
GPU_MAX=900000000
EOF

cat > "$TEST_ROOT/runtime/execution.env" <<EOF
EXECUTOR_STATE=ROLLBACK_FAILED
EXECUTOR_REASON=RESTORE_FAILURE_LATCHED
ACTIVE_DIGEST=NONE
APPLIED_PACKAGE=NONE
APPLIED_INTENT=NONE
APPLIED_ACTUATORS=ALL
APPLIED_LITTLE=NA
APPLIED_BIG=NA
APPLIED_GPU=NA
READBACK=RESTORE_FAILED
ROLLBACK_STATE=RESTORE_FAILED
APPLIED_AT=0
MONITOR_BAD_COUNT=0
MONITOR_SAMPLES=0
UPDATED_AT=$NOW
EOF

DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" resolve-latched
test ! -e "$TEST_ROOT/runtime/execution_backup.env"
grep -Fqx 'EXECUTOR_STATE=IDLE' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=LATCHED_RECHECK_RESOLVED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'LITTLE_POST_STATE=EXTERNAL' "$TEST_ROOT/runtime/execution_restore.env"
grep -Fqx 'BIG_POST_STATE=EXTERNAL' "$TEST_ROOT/runtime/execution_restore.env"
grep -Fqx 'GPU_POST_STATE=BACKUP' "$TEST_ROOT/runtime/execution_restore.env"
grep -Fq 'legacypartial123,RELEASED,LATCHED_RECHECK_EXTERNAL_OVERRIDE' "$TEST_ROOT/history/outcomes.csv"
grep -Fqx 'DIGEST=legacypartial123' "$TEST_ROOT/runtime/execution_suppress.env"
rm -f "$TEST_ROOT/runtime/execution_suppress.env"

# Restore the base fixture before the independent mixed-latch test.
printf '600000\n' > "$LP/scaling_min_freq"; printf '1800000\n' > "$LP/scaling_max_freq"
printf '900000\n' > "$BP/scaling_min_freq"; printf '2400000\n' > "$BP/scaling_max_freq"
printf '300000000\n' > "$GP/min_freq"; printf '900000000\n' > "$GP/max_freq"

# A multi-axis latch must NOT be cleared if even one owned axis still equals
# DJAEGER-applied state. This prevents blind ownership loss after partial drift.
printf '1400000\n' > "$LP/scaling_max_freq"
printf '2400000\n' > "$BP/scaling_max_freq"
printf '700000000\n' > "$GP/max_freq"
cat > "$TEST_ROOT/runtime/execution_backup.env" <<EOF
AT=$NOW
DIGEST=mixedlatch123
PACKAGE=sts.al
INTENT=PROVEN_REUSE
ACTUATORS=ALL
LITTLE_PATH=/sys/devices/system/cpu/cpufreq/policy0
LITTLE_MIN=600000
LITTLE_MAX=1800000
BIG_PATH=/sys/devices/system/cpu/cpufreq/policy6
BIG_MIN=900000
BIG_MAX=2400000
GPU_PATH=/sys/class/kgsl/kgsl-3d0/devfreq
GPU_MIN=300000000
GPU_MAX=900000000
EOF
cat > "$TEST_ROOT/runtime/execution.env" <<EOF
EXECUTOR_STATE=ROLLBACK_FAILED
EXECUTOR_REASON=RESTORE_FAILURE_LATCHED
ACTIVE_DIGEST=mixedlatch123
APPLIED_PACKAGE=sts.al
APPLIED_INTENT=PROVEN_REUSE
APPLIED_ACTUATORS=ALL
APPLIED_LITTLE=600000-1400000
APPLIED_BIG=900000-1800000
APPLIED_GPU=300000000-600000000
READBACK=RESTORE_FAILED
ROLLBACK_STATE=RESTORE_FAILED
APPLIED_AT=$NOW
MONITOR_BAD_COUNT=0
MONITOR_SAMPLES=0
UPDATED_AT=$NOW
EOF
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" resolve-latched || true
test -e "$TEST_ROOT/runtime/execution_backup.env"
grep -Fqx 'EXECUTOR_STATE=ROLLBACK_FAILED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=RESTORE_FAILURE_LATCHED' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'LITTLE_POST_STATE=APPLIED' "$TEST_ROOT/runtime/execution_restore.env"
grep -Fqx 'BIG_POST_STATE=BACKUP' "$TEST_ROOT/runtime/execution_restore.env"
grep -Fqx 'GPU_POST_STATE=EXTERNAL' "$TEST_ROOT/runtime/execution_restore.env"
rm -f "$TEST_ROOT/runtime/execution_backup.env" "$TEST_ROOT/runtime/execution_monitor.env" "$TEST_ROOT/runtime/execution_suppress.env"

# ---- APK/module atomic snapshot contract ----
SYNC_OUT=$(run_ctl sync-request 111 DJAEGER_AI_ADAPTIVE_V3 contract-test-1)
grep -Fqx 'SYNC_STATUS=VERIFIED' <<<"$SYNC_OUT"
grep -Fqx 'PAIR_VERIFIED=YES' <<<"$SYNC_OUT"
SNAPSHOT="$TEST_ROOT/cc_snapshot"
grep -Fqx 'CONTRACT=DJAEGER_AI_ADAPTIVE_V3' "$SNAPSHOT"
grep -Fqx 'MODULE_VERSION_CODE=210' "$SNAPSHOT"
grep -Fqx 'CONTROL_CENTER_VERSION_CODE=111' "$SNAPSHOT"
grep -Fqx 'PAIR_VERIFIED=YES' "$SNAPSHOT"
grep -Fqx 'WORKLOAD_CLASS=GAME' "$SNAPSHOT"
grep -Fqx 'CLOUD_HARDWARE_AUTHORITY=NONE' "$SNAPSHOT"
grep -Fqx 'PRIMARY_BRAIN=GEMINI' "$SNAPSHOT"
grep -Fqx 'DEPUTY_BRAIN=HERMES_H2' "$SNAPSHOT"
grep -Fqx 'ONE_HERMES=LOCAL_PLUS_CLOUD_ONE_IDENTITY' "$SNAPSHOT"
grep -Fqx 'HERMES_CLOUD_POLICY=ON_DEMAND_NEURON_GUARDED' "$SNAPSHOT"
grep -Fqx 'OPTIMIZATION_OBJECTIVE=HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD' "$SNAPSHOT"
grep -Fqx 'AGENT_EXECUTION_OWNER=AI_AGENT' "$SNAPSHOT"
grep -Fqx 'AGENT_EXECUTION_BACKEND=INTERNAL_EXECUTOR_WORKER' "$SNAPSHOT"
grep -Fqx 'HERMES_NEURON_USED_EST=0' "$SNAPSHOT"
grep -Fqx 'HERMES_NEURON_LIMIT=10000' "$SNAPSHOT"
grep -Fqx 'HERMES_NEURON_TIER=LIVE_DAILY_HERMES_CLOUD_USAGE' "$SNAPSHOT"
grep -Fqx 'HERMES_NEURON_STATUS=LIVE_DAILY_USAGE' "$SNAPSHOT"
grep -Fqx 'HERMES_NEURON_RESET=00:00_UTC_07:00_WIB' "$SNAPSHOT"
grep -Fqx 'HERMES_NEURON_ACCOUNTING=SUCCESSFUL_HERMES_CLOUD_ONLY_NO_FORCED_QUOTA' "$SNAPSHOT"
grep -Fqx 'PING_CURRENT_MS=22.0' "$SNAPSHOT"
grep -Fqx 'PING_AVG_MS=24.0' "$SNAPSHOT"
grep -Fqx 'PING_P95_MS=30.0' "$SNAPSHOT"
grep -Fqx 'JITTER_MS=3.0' "$SNAPSHOT"
grep -Fqx 'PACKET_LOSS_PCT=0' "$SNAPSHOT"
grep -Fqx 'QUALITY=GOOD' "$SNAPSHOT"
grep -Fq 'CONTEXT_PACKAGE=sts.al' "$SNAPSHOT"
! grep -Fq 'CPU/GPU, thermal, power, and frame behavior is being learned from the device' "$SNAPSHOT"
grep -Fq '[ "$WCLASS" != GAME ]' "$MODULE/bin/frame_observer.sh"
grep -Fq '[ "$WCLASS" != APP ]' "$MODULE/bin/frame_observer.sh"
test -r "$MODULE/uninstall.sh"
grep -Fq 'UNINSTALL_RESTORE=FAILED' "$MODULE/uninstall.sh"

# RUNTIMEFIX1 regressions.
! grep -Fq 'SKIN=$(temp_c "$(thermal_by_type' "$MODULE/bin/observer.sh"
grep -Fq 'sdm-skin-therm-usr' "$MODULE/bin/observer.sh"
grep -Fq 'gpuss-.*-usr' "$MODULE/bin/observer.sh"
grep -Fq 'THERMAL_TYPES_CACHE="$RUNTIME/thermal_types.cache"' "$MODULE/bin/observer.sh"
grep -Fq 'build_thermal_cache' "$MODULE/bin/observer.sh"
grep -Fq 'VALID_PRESENTATION_LAYER' "$MODULE/bin/frame_observer.sh"
grep -Fq 'NO_PRESENTATION_LAYER' "$MODULE/bin/frame_observer.sh"
grep -Fq 'CLOUD_MIN_INTERVAL=900' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'neuron_record_success SMART "$req" "$resp"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'neuron_record_success "$_mode" "$_req" "$_resp"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'RESET_AT_WIB=07:00' "$MODULE/bin/neuron_accounting.sh"
grep -Fq 'SOURCE=LIVE_SUCCESSFUL_HERMES_CLOUD_ONLY' "$MODULE/bin/neuron_accounting.sh"
grep -Fq 'Provider quota errors never force USED_EST to 10000' "$MODULE/bin/neuron_accounting.sh"
grep -Fq 'migration_ready' "$MODULE/service.sh"
grep -Fq 'timeout 20 sh "$MODDIR/bin/migrate.sh"' "$MODULE/service.sh"
grep -Fq 'STARTUP_SCHEMA=DJAEGER_STARTUP_V2' "$MODULE/service.sh"
grep -Fq 'SINGLETON_GUARD=ENABLED' "$MODULE/service.sh"
grep -Fq 'kill_worker_hard' "$MODULE/service.sh"
grep -Fq 'worker_pids()' "$MODULE/service.sh"
grep -Fq '/proc/[0-9]*' "$MODULE/service.sh"
grep -Fq "tr '\\000' '\\n'" "$MODULE/service.sh"
grep -Fq 'grep -Fxq "$_target"' "$MODULE/service.sh"
grep -Fq 'runtime/locks' "$MODULE/service.sh"
grep -Fq 'djaeger_singleton_claim network_observer' "$MODULE/bin/network_observer.sh"
grep -Fq 'READ_ONLY_ICMP_PROBE' "$MODULE/bin/network_observer.sh"
grep -Fq 'network_observer.sh' "$MODULE/service.sh"
grep -Fq 'djaeger_singleton_claim publisher_worker' "$MODULE/bin/publisher_worker.sh"
grep -Fq 'publisher_still_owns_lock()' "$MODULE/bin/publisher_worker.sh"
grep -Fq 'publisher_still_owns_lock || exit 0' "$MODULE/bin/publisher_worker.sh"
grep -Fq 'PUBLISHER_SELF=' "$MODULE/bin/publisher_worker.sh"

# A publisher generation whose lock ownership is replaced must self-terminate.
PUB_ROOT="$TEST_ROOT/publisher-owner-root"
mkdir -p "$PUB_ROOT/runtime/locks"
cat > "$PUB_ROOT/runtime/workload.env" <<EOF
WORKLOAD_CLASS=GAME
EOF
sh "$MODULE/bin/publisher_worker.sh" "$PUB_ROOT" "$MODULE" &
PUB_PID=$!
for _i in 1 2 3 4 5; do
  test -r "$PUB_ROOT/runtime/locks/publisher_worker.lock/pid" && break
  sleep 1
done
test -r "$PUB_ROOT/runtime/locks/publisher_worker.lock/pid"
printf '%s\n' "515151" > "$PUB_ROOT/runtime/locks/publisher_worker.lock/pid"
for _i in 1 2 3 4 5 6; do
  kill -0 "$PUB_PID" 2>/dev/null || break
  sleep 1
done
if kill -0 "$PUB_PID" 2>/dev/null; then
  echo "stale publisher generation did not self-terminate" >&2
  kill -KILL "$PUB_PID" 2>/dev/null || true
  exit 1
fi
test -d "$PUB_ROOT/runtime/locks/publisher_worker.lock"
grep -Fqx "515151" "$PUB_ROOT/runtime/locks/publisher_worker.lock/pid"
rm -rf "$PUB_ROOT/runtime/locks/publisher_worker.lock"
grep -Fq 'publisher_worker.sh' "$MODULE/service.sh"
! grep -Fq 'publish_cc "$ROOT"' "$MODULE/bin/observer.sh"
grep -Fq '_frame_ms="$(pub_kv FRAME_MS "$_frame_src")"' "$MODULE/bin/publisher.sh"
grep -Fq '_fps="$(pub_kv FPS_EST "$_frame_src")"' "$MODULE/bin/publisher.sh"
grep -Fq '_jank="$(pub_kv JANK_PCT "$_frame_src")"' "$MODULE/bin/publisher.sh"
grep -Fq '_p95="$(pub_kv P95_MS "$_frame_src")"' "$MODULE/bin/publisher.sh"
grep -Fq '_p99="$(pub_kv P99_MS "$_frame_src")"' "$MODULE/bin/publisher.sh"
! grep -Fq '_fps="$(pub_kv FPS_EST "$_snap")"' "$MODULE/bin/publisher.sh"
grep -Fq 'FRAME_NOW=$(date +%s)' "$MODULE/bin/observer.sh"
grep -Fq 'FAGE=$((FRAME_NOW-FAT))' "$MODULE/bin/observer.sh"
grep -Fq '_publish_at=$(date +%s)' "$MODULE/bin/publisher.sh"
grep -Fq 'echo "UPDATED_AT=$_publish_at"' "$MODULE/bin/publisher.sh"
grep -Fq '_observer_pid="$(cat "$_root/runtime/locks/observer.lock/pid"' "$MODULE/bin/publisher.sh"
grep -Fq 'echo "CONTROLLER_PID=$_observer_pid"' "$MODULE/bin/publisher.sh"
grep -Fq '_frame_epoch="$_frame_at"' "$MODULE/bin/publisher.sh"
grep -Fq '_thought_status=PRIMARY_OBSERVE' "$MODULE/bin/publisher.sh"
grep -Fq '_thought_status=PRIMARY_CANDIDATE' "$MODULE/bin/publisher.sh"
grep -Fq 'proposal=NONE' "$MODULE/bin/publisher.sh"
grep -Fq 'STABLE_GUARD_SEC=90' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'FRAME_DEGRADED_GUARD_SEC=45' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'URGENT_GUARD_SEC=20' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'POWER_GUARD_SEC=60' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'adaptive_guard()' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'GEMINI_GUARD_REASON=' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'GEMINI_REASONING_GUARD_REASON=' "$MODULE/bin/publisher.sh"
grep -Fq 'sleep 5' "$MODULE/bin/consensus.sh"
grep -Fq 'publish WAITING candidate_missing; sleep 10' "$MODULE/bin/shadow.sh"
grep -Fq 'insufficient_matching_frame_windows; sleep 20' "$MODULE/bin/shadow.sh"
grep -Fq 'local_synthesize_takeover()' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'TAKEOVER_LOCAL_SYNTH' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'LOCAL_FRAME_CRITICAL_RECOVERY' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'LOCAL_POWER_TRIM_GPU' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'cloud_takeover_deferred_hard_thermal_guard' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'EXECUTION="$ROOT/runtime/execution.env"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'ONE HERMES Cloud is the preferred deputy cognition' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'if cloud_takeover; then' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'HERMES_CLOUD_CONNECTION_STATUS=$_hermes_cloud_connection' "$MODULE/bin/publisher.sh"
grep -Fq 'CLOUD_LAST="$ROOT/runtime/hermes_cloud_last_success.env"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'HERMES_CLOUD_LAST_SUCCESS_AGE_SEC=' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'HERMES_CLOUD_LAST_VERDICT=' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'HERMES_CLOUD_ACTIVE=' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'HERMES_CLOUD_ACTIVE=$_hcloud_active' "$MODULE/bin/publisher.sh"
grep -Fq 'HERMES_CLOUD_LAST_VERDICT=$_hcloud_last_verdict' "$MODULE/bin/publisher.sh"
grep -Fq 'Device Truth saat ini membaca sekitar' "$MODULE/bin/publisher.sh"
grep -Fq 'Saya belum mengunci diri ke profil tetap' "$MODULE/bin/publisher.sh"
grep -Fq '_thought="$_thought Shadow baru saja lulus,' "$MODULE/bin/publisher.sh"
grep -Fq 'pub_khz_mhz()' "$MODULE/bin/publisher.sh"
grep -Fq 'pub_hz_mhz()' "$MODULE/bin/publisher.sh"
! grep -Fq '_thought="Shadow lulus kontrak frame-first/minimum-power.' "$MODULE/bin/publisher.sh"
grep -Fq 'NEURON="$ROOT/config/hermes_neuron_live.env"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq '_nupdated=$(kv UPDATED_AT "$NEURON")' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'UNRECORDED_PRE_PERSISTENCE' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'VERDICT=PENDING_PARSE' "$MODULE/bin/hermes_adapter.sh"
! grep -Fq '$LAST.tmp.$"' "$MODULE/bin/hermes_adapter.sh"
! grep -Fq '$CLOUD_LAST.tmp.$"' "$MODULE/bin/hermes_adapter.sh"
python3 - "$MODULE/bin/hermes_adapter.sh" <<'PY'
import sys
s=open(sys.argv[1],encoding='utf-8').read()
http=s.index('[ "$HTTP" = 200 ] || { HCLOUD_STATE=HTTP_ERROR; HDETAIL="cloud_takeover_http_$HTTP"')
guard=s.index('{ echo "AT=$_now"; echo "DIGEST=TAKEOVER"; } > "$LAST.tmp.$"', http)
assert http < guard, "failed Hermes Cloud request must not arm 900s success guard"
cloud=s.index('if cloud_takeover; then', s.index('ONE HERMES Cloud is the preferred deputy cognition'))
local=s.index('if local_history_takeover; then', cloud)
assert cloud < local, "Hermes Cloud must precede local-history fallback when Gemini is unavailable"
PY
grep -Fq '$4=="KEPT"' "$MODULE/bin/hermes_adapter.sh"
! grep -Fq '$4=="KEPT"||$4=="APPLIED_VERIFIED"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'INTENT=$INTENT' "$MODULE/bin/consensus.sh"
grep -Fq 'intent=="POWER_EFFICIENCY"' "$MODULE/bin/shadow.sh"
grep -Fq 'intent=="FRAME_RECOVERY"' "$MODULE/bin/shadow.sh"
grep -Fq 'APPLIED_INTENT=' "$MODULE/bin/executor.sh"
grep -Fq 'APPROVAL_INTENT_MISMATCH' "$MODULE/bin/executor.sh"
grep -Fq 'APPROVAL_ACTUATOR_MISMATCH' "$MODULE/bin/executor.sh"
grep -Fq 'APPLIED_ACTUATORS=' "$MODULE/bin/executor.sh"
grep -Fq 'ACTIVE_TRIAL_PINNED' "$MODULE/bin/executor.sh"
grep -Fq 'suppress_digest "$_digest" "$_pkg" POST_APPLY_REGRESSION 900' "$MODULE/bin/executor.sh"
grep -Fq 'RECENT_POST_APPLY_REGRESSION' "$MODULE/bin/executor.sh"
grep -Fq 'RECENT_APPLY_OR_READBACK_FAILED' "$MODULE/bin/executor.sh"
grep -Fq 'suppress_digest "$_failed_digest" "$_failed_pkg" APPLY_OR_READBACK_FAILED 900' "$MODULE/bin/executor.sh"
grep -Fq '_failed_little="${LMIN}-${LMAX}"' "$MODULE/bin/executor.sh"
grep -Fq 'resolve_restore_failure APPLY_OR_READBACK_FAILED' "$MODULE/bin/executor.sh"
grep -Fq 'suppress_digest "$_digest" "$_pkg" SYSFS_EXTERNAL_OVERRIDE 900' "$MODULE/bin/executor.sh"
grep -Fq 'recover_latched_identity()' "$MODULE/bin/executor.sh"
grep -Fq 'TARGET_LITTLE=${LMIN}-${LMAX}' "$MODULE/bin/executor.sh"
grep -Fq 'NR>1&&NF==13&&$4=="ROLLBACK_FAILED"' "$MODULE/bin/executor.sh"
grep -Fq 'AUTO_LATCHED_RECHECK' "$MODULE/bin/executor.sh"
grep -Fq 'resolve_restore_failure AUTO_LATCHED_RECHECK' "$MODULE/bin/executor.sh"
python3 - "$MODULE/bin/executor.sh" <<'PY'
import sys
s=open(sys.argv[1],encoding='utf-8').read()
r=s.index('resolve_restore_failure AUTO_LATCHED_RECHECK')
p=s.index('publish ROLLBACK_FAILED RESTORE_FAILURE_LATCHED', r)
assert r < p, "read-only resolver must run before re-latching"
block=s[s.rfind('if [ "$PREV_EXECUTOR_STATE" = ROLLBACK_FAILED',0,r):p]
assert 'restore_all' not in block, "automatic latch resolver must never write sysfs"
PY
grep -Fq 'tail -c 1 "$OUTCOMES"' "$MODULE/bin/executor.sh"
grep -Fq 'Preserve CSV row boundaries' "$MODULE/bin/executor.sh"
grep -Fq 'METHOD=DAILY_ROLLOVER_PUBLISHER' "$MODULE/bin/publisher.sh"
grep -Fq 'expected_apk=111' "$MODULE/bin/observerctl.sh"
grep -Fq '[ "$module_code" = 210 ]' "$MODULE/bin/observerctl.sh"
grep -Fq 'CANDIDATE_SWITCH_AFTER_KEEP' "$MODULE/bin/executor.sh"
grep -Fq 'APPLIED_PACKAGE="$GATE_PACKAGE"' "$MODULE/bin/executor.sh"
grep -Fq 'APPLIED_INTENT="$GATE_INTENT"' "$MODULE/bin/executor.sh"
grep -Fq 'APPLIED_ACTUATORS="$GATE_ACTUATORS"' "$MODULE/bin/executor.sh"
grep -Fq '_POLICY="$ROOT/runtime/.executor_policy.$PPID"' "$MODULE/bin/executor.sh"
grep -Fq 'active_context_safe()' "$MODULE/bin/executor.sh"
grep -Fq 'act_has "$GATE_ACTUATORS" GPU' "$MODULE/bin/executor.sh"
grep -Fq 'echo "ACTUATORS=$GATE_ACTUATORS"' "$MODULE/bin/executor.sh"
grep -Fq 'echo "ACTUATORS=$_actuators"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'echo "ACTUATORS=$ACTUATORS"' "$MODULE/bin/consensus.sh"
grep -Fq 'echo "ACTUATORS=$(kv ACTUATORS "$POLICY")"' "$MODULE/bin/shadow.sh"
grep -Fq '_approved_digest="$(kv CANDIDATE_DIGEST "$APPROVAL")"' "$MODULE/bin/shadow.sh"
grep -Fq 'rm -f "$APPROVAL"' "$MODULE/bin/shadow.sh"
grep -Fq 'RESTORE_FAILURE_LATCHED' "$MODULE/bin/executor.sh"
grep -Fq 'release_external_override()' "$MODULE/bin/executor.sh"
grep -Fq 'relinquish_no_write()' "$MODULE/bin/executor.sh"
grep -Fq 'active_readback_state()' "$MODULE/bin/executor.sh"
grep -Fq 'resolve_restore_failure()' "$MODULE/bin/executor.sh"
grep -Fq 'resolve-latched)' "$MODULE/bin/executor.sh"
grep -Fq 'RECENT_EXTERNAL_OVERRIDE' "$MODULE/bin/executor.sh"
grep -Fq 'SYSFS_EXTERNAL_OVERRIDE_CLEANUP' "$MODULE/bin/executor.sh"
grep -Fq 'RESTORED_AFTER_RACE' "$MODULE/bin/executor.sh"
grep -Fq 'RELINQUISHED_AFTER_RACE' "$MODULE/bin/executor.sh"
grep -Fq 'FAIL_AFTER_RESTORE_' "$MODULE/bin/executor.sh"
grep -Fq 'relinquish)' "$MODULE/bin/executor.sh"
grep -Fq 'EXPLICIT_RELINQUISH_NO_BACKUP' "$MODULE/bin/executor.sh"
grep -Fq 'if active_readback_ok; then rollback_active SERVICE_STOP' "$MODULE/bin/executor.sh"
grep -Fq 'else release_external_override' "$MODULE/bin/executor.sh"
grep -Fq 'SYSFS_EXTERNAL_OVERRIDE' "$MODULE/bin/executor.sh"
grep -Fq 'ROLLBACK_STATE=RELINQUISHED' "$MODULE/bin/executor.sh"
grep -Fq 'execution_restore.env' "$MODULE/bin/executor.sh"
grep -Fq 'STALE_BACKUP_RECOVERY' "$MODULE/bin/executor.sh"
grep -Fq 'LITTLE_STATUS=' "$MODULE/bin/executor.sh"
grep -Fq 'GPU_READBACK=' "$MODULE/bin/executor.sh"
grep -Fq 'GEMINI_REASONING_GUARD_REASON=' "$MODULE/bin/publisher.sh"
grep -Fq 'DEPUTY_LOCAL_SYNTH' "$MODULE/bin/publisher.sh"
grep -Fq 'CLOUD_PLAN_INTENT=' "$MODULE/bin/publisher.sh"
grep -Fq 'CLOUD_PLAN_ACTUATORS=' "$MODULE/bin/publisher.sh"
grep -Fq 'AGENT_ACTIVE_ACTUATORS=' "$MODULE/bin/publisher.sh"
grep -Fq 'NR>1&&$4=="KEPT"' "$MODULE/bin/publisher.sh"
grep -Fq 'RECENT_KEEP_ROWS=' "$MODULE/bin/learner.sh"
grep -Fq 'RECENT_ROLLBACK_FAILED_ROWS=' "$MODULE/bin/learner.sh"
grep -Fq 'VALIDATION_KEEP_ROWS=' "$MODULE/bin/learner.sh"
grep -Fq 'VALIDATION_ROLLBACK_FAILED_ROWS=' "$MODULE/bin/learner.sh"
grep -Fq 'VALIDATION_SUPERSEDED_DRIFT_ROWS=' "$MODULE/bin/learner.sh"
grep -Fq 'EXTERNAL_OVERRIDE' "$MODULE/bin/learner.sh"
grep -Fq 'LAST_OUTCOME_N=0' "$MODULE/bin/learner.sh"
grep -Fq 'PKG=$(sed -n' "$MODULE/bin/learner.sh"
grep -Fq 's/^PACKAGE=//p' "$MODULE/bin/learner.sh"
grep -Fq 'OUTN=$(awk -F, -v p="$PKG"' "$MODULE/bin/learner.sh"
grep -Fq '_recent_keep' "$MODULE/bin/publisher.sh"
grep -Fq 'RECENT_KEEP_ROWS=' "$MODULE/bin/publisher.sh"
grep -Fq 'RECENT_ROLLBACK_FAILED_ROWS=' "$MODULE/bin/publisher.sh"
grep -Fq 'VALIDATION_KEEP_ROWS=' "$MODULE/bin/publisher.sh"
grep -Fq 'VALIDATION_ROLLBACK_FAILED_ROWS=' "$MODULE/bin/publisher.sh"
grep -Fq 'VALIDATION_SUPERSEDED_DRIFT_ROWS=' "$MODULE/bin/publisher.sh"
grep -Fq 'MATURITY_PACKAGE=' "$MODULE/bin/publisher.sh"
grep -Fq 'MATURITY_MODEL_STATE=' "$MODULE/bin/publisher.sh"
grep -Fq 'MATURITY_MODEL_CONFIDENCE=' "$MODULE/bin/publisher.sh"
grep -Fq '_maturity_learning="$(pub_kv STATE "$_learn")"' "$MODULE/bin/publisher.sh"
grep -Fq '_validation_keep' "$MODULE/bin/publisher.sh"
! grep -Fq '$4=="KEPT"||$4=="APPLIED_VERIFIED"' "$MODULE/bin/publisher.sh"
grep -Fq '_rtmp="$RESTORE_DIAG.tmp.$PPID"' "$MODULE/bin/executor.sh"
grep -Fq '_frame_src="$_root/runtime/.publisher_frame.$PPID"' "$MODULE/bin/publisher.sh"
grep -Fq '_tmp="$_out.tmp.$PPID"' "$MODULE/bin/publisher.sh"
! grep -Fq 'tmp.$"' "$MODULE/bin/executor.sh"
! grep -Fq 'tmp.$"' "$MODULE/bin/publisher.sh"
grep -Fq 'thermal_pressure()' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'LOCAL_HUMAN_COMFORT_THERMAL_TRIM_GPU' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'local_synth_hard_thermal_guard' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 's<46' "$MODULE/bin/executor.sh"
grep -Fq 'b<45' "$MODULE/bin/executor.sh"
grep -Fq '_learned_samples="$(pub_kv SAMPLES "$_learn")"' "$MODULE/bin/publisher.sh"
grep -Fq 'SESSION_PACKAGE_SAMPLES=' "$MODULE/bin/publisher.sh"
grep -Fq '_thought_status=DEPUTY_LOCAL_OBSERVE' "$MODULE/bin/publisher.sh"
grep -Fq 'request_failed_http_${HTTP}' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'write_state OBSERVE non_game_workload; sleep 5' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'GEMINI_CONTEXT_PACKAGE=' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'GEMINI_CONTEXT_CLASS=' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'gemini_context_current()' "$MODULE/bin/hermes_adapter.sh"
grep -Fq '_gage' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'gemini_context_current || return 0' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'HDETAIL=non_game_workload' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'sleep 5' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'KEEP_ROWS=$(awk -F, -v p="$PKG" '\''NR>1&&$2==p&&$4=="KEPT"' "$MODULE/bin/learner.sh"
# Singleton workers must actually terminate on TERM; timeout/service stop must never hang.
TERM_ROOT="$TEST_ROOT/term-root"
mkdir -p "$TERM_ROOT/runtime/locks"
sh -c 'ROOT="$1"; . "$2"; djaeger_singleton_claim term_probe; while :; do sleep 1; done' sh "$TERM_ROOT" "$MODULE/bin/singleton.sh" &
TERM_PID=$!
sleep 1
kill -TERM "$TERM_PID"
for _i in 1 2 3 4 5; do
  kill -0 "$TERM_PID" 2>/dev/null || break
  sleep 1
done
if kill -0 "$TERM_PID" 2>/dev/null; then
  echo "singleton TERM trap did not terminate worker" >&2
  kill -KILL "$TERM_PID" 2>/dev/null || true
  exit 1
fi
! test -e "$TERM_ROOT/runtime/locks/term_probe.lock"

# A late-exiting old worker must never delete a replacement worker's lock.
OWN_ROOT="$TEST_ROOT/ownership-root"
mkdir -p "$OWN_ROOT/runtime/locks"
sh -c 'ROOT="$1"; . "$2"; djaeger_singleton_claim ownership_probe; while :; do sleep 1; done' sh "$OWN_ROOT" "$MODULE/bin/singleton.sh" &
OLD_OWNER_PID=$!
for _i in 1 2 3 4 5; do
  test -r "$OWN_ROOT/runtime/locks/ownership_probe.lock/pid" && break
  sleep 1
done
test -r "$OWN_ROOT/runtime/locks/ownership_probe.lock/pid"
printf '%s\n' "424242" > "$OWN_ROOT/runtime/locks/ownership_probe.lock/pid"
kill -TERM "$OLD_OWNER_PID"
for _i in 1 2 3 4 5; do
  kill -0 "$OLD_OWNER_PID" 2>/dev/null || break
  sleep 1
done
if kill -0 "$OLD_OWNER_PID" 2>/dev/null; then
  echo "old singleton owner did not terminate" >&2
  kill -KILL "$OLD_OWNER_PID" 2>/dev/null || true
  exit 1
fi
test -d "$OWN_ROOT/runtime/locks/ownership_probe.lock"
grep -Fqx "424242" "$OWN_ROOT/runtime/locks/ownership_probe.lock/pid"
rm -rf "$OWN_ROOT/runtime/locks/ownership_probe.lock"

grep -Fq 'djaeger_singleton_cleanup()' "$MODULE/bin/singleton.sh"
grep -Fq '[ "$_dj_owner" = "$_dj_self" ]' "$MODULE/bin/singleton.sh"

grep -Fq 'djaeger_singleton_claim gemini_reasoner' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'djaeger_singleton_claim hermes_adapter' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'djaeger_singleton_claim consensus' "$MODULE/bin/consensus.sh"
grep -Fq 'djaeger_singleton_claim shadow' "$MODULE/bin/shadow.sh"
grep -Fq 'djaeger_singleton_claim executor' "$MODULE/bin/executor.sh"
grep -Fq 'GEMINI_PRIMARY_ASSIMILATED_BY_ONE_HERMES' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'HERMES_DEPUTY_READY' "$MODULE/bin/consensus.sh"
grep -Fq 'human_comfort_frame_first_minimum_power' "$MODULE/bin/shadow.sh"
grep -Fq 's>=42' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'SOFT_SKIN_PRESSURE_C=42' "$MODULE/bin/publisher.sh"
grep -Fq 'FRAME_STABILITY_PLUS_THERMAL_COMFORT' "$MODULE/bin/publisher.sh"
grep -Fq 'comfort==1 && intent!="FRAME_RECOVERY"' "$MODULE/bin/shadow.sh"
grep -Fq 'HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD' "$MODULE/bin/consensus.sh"
grep -Fq 'CLOUD_BOOT_GUARD_SEC=120' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'restart_guard_no_cloud' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'BASELINE_SKIN_C=$(kv SKIN_TEMP_C "$SNAP")' "$MODULE/bin/executor.sh"
grep -Fq 'skin>skin0+1.0' "$MODULE/bin/executor.sh"
grep -Fq 'POST_APPLY_HUMAN_COMFORT_STABLE_' "$MODULE/bin/executor.sh"
grep -Fqx 'CREDENTIAL_SCAN_SCOPE=LEGACY_BACKUPS_TERMUX_DOWNLOAD' "$TEST_ROOT/recovery/migration.env"

echo 'module-contract-tests=PASS'
