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

rm -f "$TEST_ROOT/policy/approved.env"
DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"
grep -Fqx '1800000' "$LP/scaling_max_freq"
grep -Fqx '2400000' "$BP/scaling_max_freq"
grep -Fqx '900000000' "$GP/max_freq"

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
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"
grep -Fqx "$LP_MIN_BEFORE" "$LP/scaling_min_freq"
grep -Fqx "$LP_MAX_BEFORE" "$LP/scaling_max_freq"
grep -Fqx "$BP_MIN_BEFORE" "$BP/scaling_min_freq"
grep -Fqx "$BP_MAX_BEFORE" "$BP/scaling_max_freq"
grep -Fqx '900000000' "$GP/max_freq"

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

# Re-apply and prove active SYSFS drift is reconciled by rollback.
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
if DJAEGER_SYSFS_ROOT="$FAKE" sh "$MODULE/bin/executor.sh" "$TEST_ROOT" once; then
  echo "expected SYSFS drift to fail reconciliation" >&2
  exit 1
fi
grep -Fqx 'EXECUTOR_STATE=ROLLED_BACK' "$TEST_ROOT/runtime/execution.env"
grep -Fqx 'EXECUTOR_REASON=SYSFS_DRIFT' "$TEST_ROOT/runtime/execution.env"

# ---- APK/module atomic snapshot contract ----
SYNC_OUT=$(run_ctl sync-request 110 DJAEGER_AI_ADAPTIVE_V3 contract-test-1)
grep -Fqx 'SYNC_STATUS=VERIFIED' <<<"$SYNC_OUT"
grep -Fqx 'PAIR_VERIFIED=YES' <<<"$SYNC_OUT"
SNAPSHOT="$TEST_ROOT/cc_snapshot"
grep -Fqx 'CONTRACT=DJAEGER_AI_ADAPTIVE_V3' "$SNAPSHOT"
grep -Fqx 'MODULE_VERSION_CODE=209' "$SNAPSHOT"
grep -Fqx 'CONTROL_CENTER_VERSION_CODE=110' "$SNAPSHOT"
grep -Fqx 'PAIR_VERIFIED=YES' "$SNAPSHOT"
grep -Fqx 'WORKLOAD_CLASS=GAME' "$SNAPSHOT"
grep -Fqx 'CLOUD_HARDWARE_AUTHORITY=NONE' "$SNAPSHOT"
grep -Fqx 'PRIMARY_BRAIN=GEMINI' "$SNAPSHOT"
grep -Fqx 'DEPUTY_BRAIN=HERMES_H2' "$SNAPSHOT"
grep -Fqx 'ONE_HERMES=LOCAL_PLUS_CLOUD_ONE_IDENTITY' "$SNAPSHOT"
grep -Fqx 'HERMES_CLOUD_POLICY=ON_DEMAND_NEURON_GUARDED' "$SNAPSHOT"
grep -Fqx 'OPTIMIZATION_OBJECTIVE=FRAME_STABILITY_FIRST_MINIMUM_POWER_SECOND' "$SNAPSHOT"
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
grep -Fq 'runtime/locks' "$MODULE/service.sh"
grep -Fq 'djaeger_singleton_claim network_observer' "$MODULE/bin/network_observer.sh"
grep -Fq 'READ_ONLY_ICMP_PROBE' "$MODULE/bin/network_observer.sh"
grep -Fq 'network_observer.sh' "$MODULE/service.sh"
grep -Fq 'djaeger_singleton_claim publisher_worker' "$MODULE/bin/publisher_worker.sh"
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
grep -Fq '$4=="KEPT"' "$MODULE/bin/hermes_adapter.sh"
! grep -Fq '$4=="KEPT"||$4=="APPLIED_VERIFIED"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'INTENT=$INTENT' "$MODULE/bin/consensus.sh"
grep -Fq 'intent=="POWER_EFFICIENCY"' "$MODULE/bin/shadow.sh"
grep -Fq 'intent=="FRAME_RECOVERY"' "$MODULE/bin/shadow.sh"
grep -Fq 'APPLIED_INTENT=' "$MODULE/bin/executor.sh"
grep -Fq 'APPROVAL_INTENT_MISMATCH' "$MODULE/bin/executor.sh"
grep -Fq 'APPROVAL_ACTUATOR_MISMATCH' "$MODULE/bin/executor.sh"
grep -Fq 'APPLIED_ACTUATORS=' "$MODULE/bin/executor.sh"
grep -Fq 'act_has "$ACTUATORS" GPU' "$MODULE/bin/executor.sh"
grep -Fq 'echo "ACTUATORS=$ACTUATORS"' "$MODULE/bin/executor.sh"
grep -Fq 'echo "ACTUATORS=$_actuators"' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'echo "ACTUATORS=$ACTUATORS"' "$MODULE/bin/consensus.sh"
grep -Fq 'echo "ACTUATORS=$(kv ACTUATORS "$POLICY")"' "$MODULE/bin/shadow.sh"
grep -Fq '_approved_digest="$(kv CANDIDATE_DIGEST "$APPROVAL")"' "$MODULE/bin/shadow.sh"
grep -Fq 'rm -f "$APPROVAL"' "$MODULE/bin/shadow.sh"
grep -Fq 'RESTORE_FAILURE_LATCHED' "$MODULE/bin/executor.sh"
grep -Fq 'execution_restore.env' "$MODULE/bin/executor.sh"
grep -Fq 'STALE_BACKUP_RECOVERY' "$MODULE/bin/executor.sh"
grep -Fq 'LITTLE_STATUS=' "$MODULE/bin/executor.sh"
grep -Fq 'GPU_READBACK=' "$MODULE/bin/executor.sh"
grep -Fq 'GEMINI_REASONING_GUARD_REASON=' "$MODULE/bin/publisher.sh"
grep -Fq 'DEPUTY_LOCAL_SYNTH' "$MODULE/bin/publisher.sh"
grep -Fq 'CLOUD_PLAN_INTENT=' "$MODULE/bin/publisher.sh"
grep -Fq 'thermal_pressure()' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'LOCAL_THERMAL_POWER_TRIM_GPU' "$MODULE/bin/hermes_adapter.sh"
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

grep -Fq 'djaeger_singleton_claim gemini_reasoner' "$MODULE/bin/gemini_reasoner.sh"
grep -Fq 'djaeger_singleton_claim hermes_adapter' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'djaeger_singleton_claim consensus' "$MODULE/bin/consensus.sh"
grep -Fq 'djaeger_singleton_claim shadow' "$MODULE/bin/shadow.sh"
grep -Fq 'djaeger_singleton_claim executor' "$MODULE/bin/executor.sh"
grep -Fq 'GEMINI_PRIMARY_ASSIMILATED_BY_ONE_HERMES' "$MODULE/bin/hermes_adapter.sh"
grep -Fq 'HERMES_DEPUTY_READY' "$MODULE/bin/consensus.sh"
grep -Fq 'frame_priority_then_minimum_power' "$MODULE/bin/shadow.sh"
grep -Fqx 'CREDENTIAL_SCAN_SCOPE=LEGACY_BACKUPS_TERMUX_DOWNLOAD' "$TEST_ROOT/recovery/migration.env"

echo 'module-contract-tests=PASS'
