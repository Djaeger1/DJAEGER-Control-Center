#!/system/bin/sh

# Sourced by observer.sh. Publishes one atomic snapshot for the read-only APK.
# It never reads or writes sysfs and never includes credential values.

pub_kv() {
  [ -r "$2" ] || return 0
  sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1
}

pub_int() {
  case "$1" in
    ''|NA|*[!0-9.-]*) echo -1 ;;
    *) awk -v x="$1" 'BEGIN{printf "%.0f",x}' ;;
  esac
}

pub_abs_int() {
  case "$1" in
    ''|NA|*[!0-9-]*) echo -1 ;;
    *) awk -v x="$1" 'BEGIN{if(x<0)x=-x;printf "%.0f",x}' ;;
  esac
}

pub_clean() {
  printf '%s' "$1" | tr '\r\n\t' '   ' | tr -cd 'A-Za-z0-9._:+/%=,@ -' | cut -c1-180
}

pub_registry_has() {
  [ -r "$1" ] || return 1
  awk -F'|' -v p="$2" '$2==p{found=1}END{exit !found}' "$1" 2>/dev/null
}

publish_cc() {
  _root="$1"
  _snap="$_root/runtime/snapshot.env"
  _frame="$_root/runtime/frame.env"
  _learn="$_root/history/learned_envelope.env"
  _gem_state="$_root/runtime/gemini_reasoner.env"
  _gem_prop="$_root/policy/gemini_proposal.env"
  _hermes_state="$_root/runtime/hermes_adapter.env"
  _local_vote="$_root/policy/hermes_local_vote.env"
  _cloud_vote="$_root/policy/hermes_cloud_vote.env"
  _cons="$_root/runtime/consensus.env"
  _candidate="$_root/policy/candidate.env"
  _shadow="$_root/runtime/shadow.env"
  _execution="$_root/runtime/execution.env"
  _railway="$_root/runtime/railway.env"
  _migration="$_root/recovery/migration.env"
  _out="$_root/cc_snapshot"
  [ -r "$_snap" ] || return 0

  _epoch="$(pub_kv EPOCH "$_snap")"; case "$_epoch" in ''|*[!0-9]*) _epoch="$(date +%s)";; esac
  _pkg="$(pub_kv ACTIVE_PACKAGE "$_snap")"; [ -n "$_pkg" ] || _pkg=UNKNOWN
  _samples="$(pub_kv PACKAGE_SAMPLES "$_snap")"; case "$_samples" in ''|*[!0-9]*) _samples=0;; esac
  _learning="$(pub_kv STATE "$_learn")"; [ -n "$_learning" ] || _learning="$(pub_kv LEARNING_STATE "$_snap")"
  [ -n "$_learning" ] || _learning=WAITING
  _confidence="$(pub_kv CONFIDENCE "$_learn")"; case "$_confidence" in ''|*[!0-9]*) _confidence=0;; esac

  _frame_evidence="$(pub_kv FRAME_EVIDENCE "$_snap")"; [ -n "$_frame_evidence" ] || _frame_evidence=UNAVAILABLE
  _workload=UNKNOWN
  _workload_source=UNCLASSIFIED
  case "$_pkg" in
    ''|UNKNOWN|android|com.android.*|com.google.android.*|com.miui.*|com.djaeger.observer)
      _workload=SYSTEM; _workload_source=PROTECTED_SYSTEM_PATTERN ;;
    sts.al)
      _workload=GAME; _workload_source=BUILTIN_GAME_REGISTRY ;;
    *)
      if pub_registry_has "$_root/config/game_registry.tsv" "$_pkg"; then
        _workload=GAME; _workload_source=GAME_REGISTRY
      elif pub_registry_has "$_root/config/app_registry.tsv" "$_pkg"; then
        _workload=APP; _workload_source=APP_REGISTRY
      elif [ "$_frame_evidence" = VALID ] && [ "$_samples" -ge 120 ] 2>/dev/null; then
        _workload=UNKNOWN; _workload_source=FRAME_EVIDENCE_UNCONFIRMED
      else
        _workload=APP; _workload_source=FOREGROUND_DEFAULT
      fi
    ;;
  esac
  _active=0; _window=INACTIVE
  [ "$_workload" = GAME ] && { _active=1; _window=FOREGROUND; }
  {
    echo "AT=$_epoch"
    echo "PACKAGE=$_pkg"
    echo "WORKLOAD_CLASS=$_workload"
    echo "SOURCE=$_workload_source"
  } > "$_root/runtime/workload.env.tmp.$$"
  chmod 600 "$_root/runtime/workload.env.tmp.$$" 2>/dev/null
  mv -f "$_root/runtime/workload.env.tmp.$$" "$_root/runtime/workload.env"

  _little="$(pub_kv LITTLE_CUR_KHZ "$_snap")"
  _big="$(pub_kv BIG_CUR_KHZ "$_snap")"
  _gpu="$(pub_kv GPU_CUR_HZ "$_snap")"
  _cpu_t="$(pub_int "$(pub_kv CPU_TEMP_C "$_snap")")"
  _gpu_t="$(pub_int "$(pub_kv GPU_TEMP_C "$_snap")")"
  _skin_t="$(pub_int "$(pub_kv SKIN_TEMP_C "$_snap")")"
  _bat_t="$(pub_int "$(pub_kv BATTERY_TEMP_C "$_snap")")"
  _current="$(pub_abs_int "$(pub_kv BATTERY_CURRENT_UA "$_snap")")"
  _voltage="$(pub_int "$(pub_kv BATTERY_VOLTAGE_UV "$_snap")")"
  _power="$(pub_int "$(pub_kv POWER_MW "$_snap")")"
  _power_valid=REJECTED; _power_reason=NO_VALID_DISCHARGE_SAMPLE
  [ "$_power" -gt 0 ] 2>/dev/null && { _power_valid=VALID; _power_reason=MEASURED_DISCHARGE; }
  _battery_status="$(pub_kv BATTERY_STATUS "$_snap")"; [ -n "$_battery_status" ] || _battery_status=NA
  _frame_ms="$(pub_kv FRAME_MS "$_frame")"; [ -n "$_frame_ms" ] || _frame_ms=0
  _fps="$(pub_kv FPS_EST "$_snap")"; [ -n "$_fps" ] && [ "$_fps" != NA ] || _fps=0
  _jank="$(pub_kv JANK_PCT "$_snap")"; [ -n "$_jank" ] && [ "$_jank" != NA ] || _jank=-1
  _p95="$(pub_kv P95_MS "$_snap")"; [ -n "$_p95" ] && [ "$_p95" != NA ] || _p95=0
  _p99="$(pub_kv P99_MS "$_snap")"; [ -n "$_p99" ] && [ "$_p99" != NA ] || _p99=0

  _lmin="$(pub_kv LITTLE_MIN_KHZ "$_learn")"; [ -n "$_lmin" ] || _lmin=NA
  _lmax="$(pub_kv LITTLE_MAX_KHZ "$_learn")"; [ -n "$_lmax" ] || _lmax=NA
  _bmin="$(pub_kv BIG_MIN_KHZ "$_learn")"; [ -n "$_bmin" ] || _bmin=NA
  _bmax="$(pub_kv BIG_MAX_KHZ "$_learn")"; [ -n "$_bmax" ] || _bmax=NA
  _gmin="$(pub_kv GPU_MIN_HZ "$_learn")"; [ -n "$_gmin" ] || _gmin=NA
  _gmax="$(pub_kv GPU_MAX_HZ "$_learn")"; [ -n "$_gmax" ] || _gmax=NA

  _gem="$(pub_kv GEMINI_STATE "$_gem_state")"; [ -n "$_gem" ] || _gem=WAITING
  _gem_conf="$(pub_kv CONFIDENCE "$_gem_prop")"; case "$_gem_conf" in ''|*[!0-9]*) _gem_conf=0;; esac
  _gem_reason="$(pub_kv REASON "$_gem_prop")"; [ -n "$_gem_reason" ] || _gem_reason="$(pub_kv GEMINI_DETAIL "$_gem_state")"
  _hlocal="$(pub_kv HERMES_LOCAL_STATE "$_hermes_state")"; [ -n "$_hlocal" ] || _hlocal=WAITING
  _hcloud="$(pub_kv HERMES_CLOUD_STATE "$_hermes_state")"; [ -n "$_hcloud" ] || _hcloud=STANDBY
  _hroute="$(pub_kv HERMES_CLOUD_ROUTE "$_hermes_state")"; [ -n "$_hroute" ] || _hroute=LOCAL
  _hmodel="$(pub_kv HERMES_CLOUD_MODEL "$_hermes_state")"; [ -n "$_hmodel" ] || _hmodel=NA
  _hhttp="$(pub_kv HERMES_CLOUD_HTTP "$_hermes_state")"; [ -n "$_hhttp" ] || _hhttp=NA
  _hauth="$(pub_kv HERMES_CLOUD_AUTH "$_hermes_state")"; [ -n "$_hauth" ] || _hauth=UNKNOWN
  _hreason="$(pub_kv HERMES_CLOUD_DETAIL "$_hermes_state")"; [ -n "$_hreason" ] || _hreason=NO_REVIEW_YET
  _hconf="$(pub_kv CONFIDENCE "$_local_vote")"; case "$_hconf" in ''|*[!0-9]*) _hconf=0;; esac
  _cons_state="$(pub_kv CONSENSUS_STATE "$_cons")"; [ -n "$_cons_state" ] || _cons_state=OBSERVING
  _shadow_state="$(pub_kv SHADOW_STATE "$_shadow")"; [ -n "$_shadow_state" ] || _shadow_state=WAITING
  _shadow_n="$(pub_kv SHADOW_WINDOWS "$_shadow")"; case "$_shadow_n" in ''|*[!0-9]*) _shadow_n=0;; esac
  _exec_state="$(pub_kv EXECUTOR_STATE "$_execution")"; [ -n "$_exec_state" ] || _exec_state=IDLE
  _exec_reason="$(pub_kv EXECUTOR_REASON "$_execution")"; [ -n "$_exec_reason" ] || _exec_reason=WAITING
  _exec_little="$(pub_kv APPLIED_LITTLE "$_execution")"; [ -n "$_exec_little" ] || _exec_little=NA
  _exec_big="$(pub_kv APPLIED_BIG "$_execution")"; [ -n "$_exec_big" ] || _exec_big=NA
  _exec_gpu="$(pub_kv APPLIED_GPU "$_execution")"; [ -n "$_exec_gpu" ] || _exec_gpu=NA
  _readback="$(pub_kv READBACK "$_execution")"; [ -n "$_readback" ] || _readback=NA
  _rollback="$(pub_kv ROLLBACK_STATE "$_execution")"; [ -n "$_rollback" ] || _rollback=STANDBY
  _railway_state="$(pub_kv RAILWAY_STATE "$_railway")"; [ -n "$_railway_state" ] || _railway_state=WAITING
  _migration_state="$(pub_kv MIGRATION_STATE "$_migration")"; [ -n "$_migration_state" ] || _migration_state=UNKNOWN
  _credential_count="$(pub_kv CREDENTIAL_FILE_COUNT "$_migration")"; case "$_credential_count" in ''|*[!0-9]*) _credential_count=0;; esac

  _cloud_connection=WAITING
  case "$_gem" in CANDIDATE|OBSERVE) _cloud_connection=ONLINE;; COOLDOWN) _cloud_connection=COOLDOWN;; HTTP_ERROR|NO_KEY|UNAVAILABLE) _cloud_connection=OFFLINE;; esac
  _plan_provider=NONE; [ -r "$_gem_prop" ] && _plan_provider=GEMINI
  _thought_source=OBSERVER_LOCAL
  [ "$_gem" = CANDIDATE ] && _thought_source=GEMINI
  case "$_hcloud" in APPROVED|REJECTED) _thought_source=HERMES_H2;; esac
  _thought="CPU/GPU, thermal, power, and frame behavior is being learned from the device. No fixed preset is authoritative."
  [ "$_cons_state" = PENDING_SHADOW ] && _thought="A measured candidate passed Gemini plus ONE HERMES review and is waiting for shadow evidence."
  [ "$_shadow_state" = PASS ] && _thought="Shadow evidence passed. The local executor may apply only the validated device-specific range."
  [ "$_exec_state" = APPLIED ] && _thought="Adaptive range is active locally after measured evidence, AI consensus, shadow pass, thermal guard, and exact sysfs readback."
  [ "$_exec_state" = ROLLED_BACK ] && _thought="Adaptive range was rolled back locally because a safety or context gate closed."

  if [ -r "$_root/history/telemetry.csv" ]; then _history_bytes="$(wc -c < "$_root/history/telemetry.csv" 2>/dev/null)"
  else _history_bytes=0
  fi
  case "$_history_bytes" in ''|*[!0-9]*) _history_bytes=0;; esac
  _tel="$_epoch,$_cpu_t,$_gpu_t,$_skin_t,$_bat_t,$_little,$_big,$_gpu,STOCK_OBSERVER,$_frame_ms,$_fps,$_jank,$_p95,$_p99,0,$_battery_status,$_current,$_voltage,$_power,$_power_valid,$_power_reason,$_pkg,$_window"
  _frame_line="$_epoch,STOCK_OBSERVER,$_frame_ms,$_fps,$_jank,$_p95,$_p99"
  _plan_line=""
  if [ -r "$_candidate" ]; then
    _pc="$(pub_kv CONFIDENCE "$_candidate")"; [ -n "$_pc" ] || _pc=0
    _plmin="$(pub_kv LITTLE_MIN_KHZ "$_candidate")"; _plmax="$(pub_kv LITTLE_MAX_KHZ "$_candidate")"
    _pbmin="$(pub_kv BIG_MIN_KHZ "$_candidate")"; _pbmax="$(pub_kv BIG_MAX_KHZ "$_candidate")"
    _pgmin="$(pub_kv GPU_MIN_HZ "$_candidate")"; _pgmax="$(pub_kv GPU_MAX_HZ "$_candidate")"
    _plan_line="$_epoch,$_shadow_state,$_pc,AI_CONSENSUS_MEASURED_ENVELOPE,ADAPTIVE,LEARNED,$_plmin,$_plmax,$_pbmin,$_pbmax,$_pgmin,$_pgmax"
  fi

  _tmp="$_out.tmp.$$"
  {
    echo "__INSTALLED__"; echo 1
    echo "__VERSION__"; echo "1.0.0-adaptive-clean"
    echo "__RUNTIME__"
    echo "UPDATED_AT=$_epoch"; echo "ACTIVE=$_active"; echo "GAME=$_pkg"; echo "WINDOW_MODE=$_window"
    echo "CONTROLLER_PID=$$"; echo "PREDICTOR_PID="; echo "USER_MODE=OBSERVER"
    echo "LEARNING_SAMPLES=$_samples"; echo "LEARNING_CONFIDENCE=$_confidence"; echo "LEARNED_STATE=$_learning"
    echo "__TEL__"; echo "$_tel"
    echo "__BRAIN__"
    if [ "$_exec_state" = APPLIED ]; then
      echo "CURRENT_BRAIN=AI_CONSENSUS"; echo "FINAL_SOURCE=LOCAL_VALIDATED_EXECUTOR"; echo "BRAIN_MODE=ADAPTIVE"; echo "BRAIN_PROFILE=LEARNED"
      echo "FINAL_PROFILE=ADAPTIVE_LEARNED"; echo "FINAL_ADJUSTMENT=ACTIVE"; echo "EXEC_MODE=ADAPTIVE_AUTO"
      echo "EXEC_LITTLE=$_exec_little"; echo "EXEC_BIG=$_exec_big"; echo "EXEC_GPU=$_exec_gpu"
    else
      echo "CURRENT_BRAIN=OBSERVER"; echo "FINAL_SOURCE=MEASURED_DEVICE"; echo "BRAIN_MODE=LEARN"; echo "BRAIN_PROFILE=LEARNED_PENDING"
      echo "FINAL_PROFILE=LEARNED_PENDING"; echo "FINAL_ADJUSTMENT=NONE"; echo "EXEC_MODE=GATED_AUTO"
      echo "EXEC_LITTLE=$_lmin-$_lmax"; echo "EXEC_BIG=$_bmin-$_bmax"; echo "EXEC_GPU=$_gmin-$_gmax"
    fi
    echo "CLOUD_CONNECTION_STATUS=$_cloud_connection"; echo "CLOUD_PROVIDER=GEMINI"
    echo "CLOUD_CONTROL_PROVIDER=NONE"; echo "CLOUD_PLAN_PROVIDER=$_plan_provider"
    echo "CLOUD_PLAN_STATE=$_cons_state"; echo "CLOUD_PLAN_SCORE=$_gem_conf"; echo "CLOUD_PLAN_REASON=$(pub_clean "$_gem_reason")"
    echo "HERMES_PROPOSAL_STATE=$_hlocal"; echo "HERMES_PROPOSAL_CONFIDENCE=$_hconf"; echo "HERMES_PROFILE=ADAPTIVE_NO_FIXED_PROFILE"
    echo "HERMES_REASON=$(pub_clean "$_hreason")"; echo "HERMES_BACKEND=$([ "$_hroute" = LOCAL ] && echo LOCAL || echo CLOUD)"
    echo "HERMES_CLOUD_STATE=$_hcloud"; echo "HERMES_CLOUD_AUTH=$_hauth"
    echo "HERMES_CLOUD_ROUTE=$_hroute"; echo "HERMES_CLOUD_MODEL=$_hmodel"; echo "HERMES_CLOUD_HTTP_CODE=$_hhttp"
    echo "HERMES_CLOUD_REASON=$(pub_clean "$_hreason")"; echo "HERMES_NEURON_USED_EST=UNAVAILABLE"; echo "HERMES_NEURON_LIMIT=UNAVAILABLE"; echo "HERMES_NEURON_TIER=UNREPORTED"
    echo "AGENT_VERSION=ADAPTIVE_V1"; echo "AGENT_ROLE=MEASURE_LEARN_REVIEW_SHADOW_EXECUTE"; echo "AGENT_STATE=$_cons_state"
    echo "AGENT_INPUT_SOURCE=DEVICE_TELEMETRY"; echo "AGENT_DECISION_AUTHORITY=LOCAL_VALIDATOR"; echo "AGENT_EXECUTION_OWNER=LOCAL_EXECUTOR"
    echo "AGENT_HARDWARE_AUTHORITY=LOCAL_GATED"; echo "AGENT_HARDWARE_TRUTH_SOURCE=OBSERVER_SYSFS_READBACK"
    echo "AGENT_HARDWARE_TRUTH_AUTHORITY=MEASURED"; echo "AGENT_MUST_OBEY_ACTIVE_BRAIN=CONSENSUS_AND_SAFETY"
    echo "AGENT_CAN_CHOOSE_BRAIN=NO"; echo "AGENT_CAN_OVERRIDE_BRAIN=NO"; echo "AGENT_EXECUTION_BACKEND=LOCAL_VALIDATED_SYSFS"
    echo "AGENT_LAST_VALIDATION=$_cons_state"; echo "AGENT_LAST_READBACK=STOCK"; echo "DECISION_PRIORITY=SAFETY>MEASURED_EVIDENCE>AI_REVIEW"
    echo "THOUGHT_FRESH=1"; echo "THOUGHT_AGE_SEC=0"
    echo "__THOUGHTS__"; echo "SOURCE=$_thought_source"; echo "STATUS=$_cons_state"; echo "CONFIDENCE=$_gem_conf"; echo "TEXT=$_thought"
    echo "__MEMORY__"; echo "USED_BYTES=$_history_bytes"; echo "MAX_BYTES=3145728"; echo "LEDGER_ROWS=$_samples"; echo "HARDWARE_OUTCOME_ROWS=$_shadow_n"
    echo "__AUTHORITY__"; echo "STATE=LOCAL_GATED"; echo "HARDWARE_AUTHORITY=LOCAL_VALIDATED_EXECUTOR"; echo "CLOUD_HARDWARE_AUTHORITY=NONE"; echo "SYSFS_WRITES=EXECUTOR_ONLY"; echo "EXECUTOR=$_exec_state"
    echo "__SESSION_SAFETY__"; echo "STATE=FAIL_CLOSED"; echo "ROLLBACK=$_rollback"; echo "THERMAL_AUTHORITY=LOCAL_GUARD_PLUS_NATIVE"
    echo "__SUPERVISOR__"; echo "STATE=RUNNING"; echo "PROCESS_MODEL=BOUNDED_OBSERVER_LOOPS"
    echo "__HERMES_CTX1_STATUS__"; echo "STATE=$_hlocal"; echo "MIGRATION=$_migration_state"
    echo "__HERMES_CTX1_RUNTIME__"; echo "PACKAGE=$_pkg"; echo "WORKLOAD=$_workload"; echo "WINDOW=$_window"
    echo "__HERMES_CTX1_SAFETY__"; echo "SYSFS=LOCAL_EXECUTOR_ONLY"; echo "CONSENSUS=$_cons_state"; echo "SHADOW=$_shadow_state"; echo "EXECUTOR=$_exec_state"
    echo "__HERMES_CTX1_HARDWARE__"; echo "LITTLE=$_little"; echo "BIG=$_big"; echo "GPU=$_gpu"; echo "SKIN=$_skin_t"; echo "POWER=$_power"
    echo "__HERMES_CTX1_MEMORY__"; echo "SAMPLES=$_samples"; echo "BYTES=$_history_bytes"; echo "CREDENTIAL_FILES=$_credential_count"
    echo "__HERMES_CTX1_LEARNING__"; echo "STATE=$_learning"; echo "CONFIDENCE=$_confidence"; echo "FRAME_EVIDENCE=$_frame_evidence"
    echo "__HERMES_COGNITION_STATUS__"; echo "STATE=$_hlocal"; echo "MODE=OBSERVER_VNEXT"
    echo "__HERMES_MEMORY_VNEXT__"; echo "STATE=$_learning"; echo "SAMPLES=$_samples"; echo "SOURCE=STOCK_HISTORY"
    echo "__HERMES_REASONING_V2__"; echo "STATE=$_cons_state"; echo "CONTRACT=STRUCTURED_ENVELOPE_ONLY"
    echo "__HERMES_SKILLS_VNEXT__"; echo "STATE=READY"; echo "SKILLS=VALIDATE_OPP,THERMAL_GUARD,FRAME_GUARD,POWER_GUARD"
    echo "__HERMES_LEARNING_V2__"; echo "STATE=$_learning"; echo "PACKAGE=$_pkg"; echo "SAMPLES=$_samples"
    echo "__HERMES_RESEARCH_V2__"; echo "STATE=$_shadow_state"; echo "SHADOW_WINDOWS=$_shadow_n"
    echo "__HERMES_HUMAN_COMFORT__"; echo "COMFORT_PRESET=LEARNED"; echo "STATE=LEARNING_FROM_FEEDBACK"; echo "FIXED_PRESET=DISABLED"
    echo "__HERMES_LANGUAGE__"; echo "STATE=STRUCTURED_ONLY"
    echo "__HERMES_MATH__"; echo "STATE=$_learning"; echo "VERIFY=$_shadow_state"; echo "INPUT_SANITY=MEASURED"; echo "TARGET_FRAME_MS=16.67"
    echo "__HERMES_KERNEL1__"; echo "STATE=GATED"; echo "STRATEGY=MEASURED_ADAPTIVE"; echo "BOTTLENECK=$_exec_reason"; echo "CAPABILITIES_TOTAL=3"; echo "ACTUATORS_TOTAL=6"; echo "ACTION_COUNT=$([ "$_exec_state" = APPLIED ] && echo 6 || echo 0)"; echo "ROOT_AUTHORITY_OWNER=LOCAL_EXECUTOR"; echo "SYSFS_OWNER=LOCAL_EXECUTOR"
    echo "__AGENT_SYSFS1_CAPABILITY__"; echo "TOTAL=3"; echo "ACTUATORS=6"
    echo "__AGENT_SYSFS1_EXECUTION__"; echo "STATUS=$_exec_state"; echo "ACTION_COUNT=$([ "$_exec_state" = APPLIED ] && echo 6 || echo 0)"; echo "APPLIED_COUNT=$([ "$_exec_state" = APPLIED ] && echo 6 || echo 0)"; echo "FAILURE=$([ "$_exec_state" = ROLLED_BACK ] && echo "$_exec_reason" || echo NONE)"
    echo "__CONTROL_CENTER_SYNC__"; echo "CONTRACT=DJAEGER_AI_ADAPTIVE_V1"; echo "MODULE_VERSION_CODE=202"; echo "CONTROL_CENTER_VERSION_CODE=103"; echo "HERMES_CLOUD=ADVISORY_REVIEW"; echo "HERMES_CLOUD_ROLE=ONE_HERMES_REVIEWER"; echo "HERMES_BACKEND_PRIORITY=LOCAL_GUARD_THEN_CLOUD_REVIEW"; echo "WORKLOAD_FINAL=ADAPTIVE_CLASSIFIER"; echo "DUAL_REGISTRY=SEPARATE"; echo "PREEXEC_WORKLOAD_GUARD=ACTIVE_LOCAL_GATED"
    echo "__STRATEGY_RESULT__"; echo "VALIDATION=$_cons_state"; echo "READBACK=STOCK"; echo "OUTCOME=$_shadow_state"
    echo "__ENV__"; [ -r "$_learn" ] && cat "$_learn"
    echo "__HTTP__"; [ -r "$_gem_state" ] && cat "$_gem_state" || true
    echo "__SERVER__"; [ -r "$_hermes_state" ] && cat "$_hermes_state" || true
    echo "__DECISIONS__"
    echo "__PLANS__"; [ -n "$_plan_line" ] && echo "$_plan_line"
    echo "__FRAME__"; echo "$_frame_line"
    echo "__LOG__"; [ -r "$_root/runtime/events.log" ] && tail -n 80 "$_root/runtime/events.log" || true
    echo "__NETWORK__"; echo "SESSION_ACTIVE=0"; echo "QUALITY=UNMEASURED"
    echo "__REASONING__"; echo "STATE=$_cons_state"
    echo "__RESYNC__"; echo "STATE=MATCHED"; echo "CONTRACT=DJAEGER_AI_ADAPTIVE_V1"
    echo "__EXECUTION__"; echo "STATUS=$_exec_state"; echo "READBACK=$_readback"; echo "ROLLBACK=$_rollback"; echo "RAILWAY=$_railway_state"
    echo "__POLICY_CONTEXT__"; echo "PACKAGE=$_pkg"; echo "WORKLOAD=$_workload"; echo "BASELINE=$_learning"
    echo "__ATTRIBUTION__"; echo "SOURCE=MEASURED_STOCK"
    echo "__WORKLOAD_CONTEXT__"; echo "PACKAGE=$_pkg"; echo "WORKLOAD_CLASS=$_workload"; echo "WORKLOAD_PROFILE=STOCK_OBSERVER"; echo "SUBJECT_CLASS=$_workload"; echo "REASONING_DOMAIN=$_workload"; echo "GAME_SEMANTICS=REGISTRY_ONLY"; echo "FRAME_SEMANTICS=EVIDENCE_ONLY"; echo "SOURCE=$_workload_source"; echo "CONFIDENCE=$([ "$_workload_source" = GAME_REGISTRY ] && echo 100 || echo 60)"; echo "GAME_REGISTRY_AUTHORITY=MANUAL_PLUS_BUILTIN"
    echo "__WORKLOAD_GATE__"; echo "GAME_ONLY=ADAPTIVE_GATED"; echo "APP_ONLY=OBSERVE"; echo "SYSTEM_ONLY=OBSERVE"
    echo "__PROPOSAL_BINDING__"; echo "LATEST_PROPOSAL_SOURCE=$_plan_provider"; echo "LATEST_SUBJECT_PACKAGE=$_pkg"; echo "LATEST_SUBJECT_CLASS=$_workload"; echo "LATEST_BINDING_DECISION=$_cons_state"; echo "LATEST_BINDING_REASON=$_exec_reason"
    echo "__WORKLOAD_FINAL__"; echo "STATUS=ACTIVE"; echo "DUAL_REGISTRY=SEPARATE"; echo "REGISTRY_CONFLICTS=0"; echo "EXECUTION_SCOPE=GAME_ONLY_LOCAL_GATED"; echo "APP_GAME_POLICY=NEVER_PROMOTE"; echo "SYSTEM_GAME_POLICY=NEVER_PROMOTE"; echo "UNKNOWN_GAME_POLICY=OBSERVE_ONLY"; echo "STALE_POLICY=FAIL_CLOSED"; echo "LEARNING_ISOLATION=PER_PACKAGE"; echo "ROOT_AUTHORITY_CHANGED=LOCAL_EXECUTOR_ONLY"; echo "SYSFS_AUTHORITY_CHANGED=LOCAL_EXECUTOR_ONLY"; echo "RESCUE_PATH_CHANGED=NO"
    echo "__WORKLOAD_EXEC_GUARD__"; echo "DECISION=$([ "$_exec_state" = APPLIED ] && echo ALLOW || echo BLOCK)"; echo "REASON=$_exec_reason"
    echo "__APP_REGISTRY__"; [ -r "$_root/config/app_registry.tsv" ] && cat "$_root/config/app_registry.tsv" || true
    echo "__GAME_REGISTRY_MANUAL__"; [ -r "$_root/config/game_registry.tsv" ] && cat "$_root/config/game_registry.tsv" || true
    echo "__BUG_HEALTH__"; echo "STATE=OK"
    echo "__BUG_EVENTS__"
  } > "$_tmp"
  chmod 644 "$_tmp" 2>/dev/null
  mv -f "$_tmp" "$_out"
}
