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

pub_clean_long() {
  printf '%s' "$1" | tr '\r\n\t' '   ' | tr -cd 'A-Za-z0-9._:+/%=,@ -' | cut -c1-1200
}

pub_khz_mhz() {
  case "$1" in ''|NA|*[!0-9]*) echo NA ;; *) awk -v x="$1" 'BEGIN{printf "%.0f",x/1000}' ;; esac
}

pub_hz_mhz() {
  case "$1" in ''|NA|*[!0-9]*) echo NA ;; *) awk -v x="$1" 'BEGIN{printf "%.0f",x/1000000}' ;; esac
}

pub_registry_has() {
  [ -r "$1" ] || return 1
  awk -F'|' -v p="$2" '$2==p{found=1}END{exit !found}' "$1" 2>/dev/null
}

pub_age_sec() {
  _v="$(pub_kv "$2" "$1")"
  case "$_v" in ''|*[!0-9]*) echo 999999;; *) _n=$(date +%s); _a=$((_n-_v)); [ "$_a" -ge 0 ] 2>/dev/null || _a=999999; echo "$_a";; esac
}

pub_fresh() {
  _a="$(pub_age_sec "$1" "$2")"
  [ "$_a" -le "$3" ] 2>/dev/null && echo "FRESH:$_a" || echo "STALE:$_a"
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
  _hermes_plan="$_root/policy/hermes_proposal.env"
  _cons="$_root/runtime/consensus.env"
  _candidate="$_root/policy/candidate.env"
  _shadow="$_root/runtime/shadow_contextual_v4.env"
  _execution="$_root/runtime/execution.env"
  _outcomes="$_root/history/outcomes.csv"
  _railway="$_root/runtime/railway.env"
  _network="$_root/runtime/network.env"
  _recovery="$_root/runtime/credential_recovery.env"
  _neuron="$_root/config/hermes_neuron_live.env"
  _migration="$_root/recovery/migration.env"
  _handshake="$_root/runtime/handshake.env"
  _gem_vault="$_root/config/gemini_vault.env"
  _gem_cooldown="$_root/config/gemini_cooldown.env"
  _hermes_cfg="$_root/config/hermes_cloud.env"
  _genfile="$_root/runtime/snapshot_generation"
  _out="$_root/cc_snapshot"
  [ -r "$_snap" ] || return 0

  _epoch="$(pub_kv EPOCH "$_snap")"; case "$_epoch" in ''|*[!0-9]*) _epoch="$(date +%s)";; esac
  _pkg="$(pub_kv ACTIVE_PACKAGE "$_snap")"; [ -n "$_pkg" ] || _pkg=UNKNOWN
  _seq="$(pub_kv SAMPLE_SEQ "$_snap")"; case "$_seq" in ''|*[!0-9]*) _seq=0;; esac
  _top_pkg="$(pub_kv TOP_PACKAGE "$_snap")"; [ -n "$_top_pkg" ] || _top_pkg="$_pkg"
  _visible_game="$(pub_kv VISIBLE_GAME "$_snap")"; [ -n "$_visible_game" ] || _visible_game=NONE
  _pkg_source="$(pub_kv PACKAGE_SOURCE "$_snap")"; [ -n "$_pkg_source" ] || _pkg_source=LEGACY_FOREGROUND
  _session_samples="$(pub_kv PACKAGE_SAMPLES "$_snap")"; case "$_session_samples" in ''|*[!0-9]*) _session_samples=0;; esac
  _samples="$_session_samples"
  _learn_pkg="$(pub_kv PACKAGE "$_learn")"
  if [ -n "$_learn_pkg" ] && [ "$_learn_pkg" = "$_pkg" ]; then
    _learning="$(pub_kv STATE "$_learn")"
    _confidence="$(pub_kv CONFIDENCE "$_learn")"; case "$_confidence" in ''|*[!0-9]*) _confidence=0;; esac
    _learned_samples="$(pub_kv SAMPLES "$_learn")"; case "$_learned_samples" in ''|*[!0-9]*) _learned_samples=0;; esac
    [ "$_learned_samples" -gt "$_samples" ] 2>/dev/null && _samples="$_learned_samples"
  else
    _learning="$(pub_kv LEARNING_STATE "$_snap")"
    _confidence=0
  fi
  [ -n "$_learning" ] || _learning=WAITING

  # Read the frame worker as one coherent source for every frame metric.
  # Previously FRAME_MS came from frame.env while FPS/JANK/P95/P99 came from
  # observer snapshot.env, which could produce impossible mixed UI states such
  # as "Frame 16.7 ms" together with "FPS — / Jank —".
  _frame_src="$_root/runtime/.publisher_frame.$PPID"
  if [ -r "$_frame" ]; then
    cp "$_frame" "$_frame_src" 2>/dev/null || :
  fi
  [ -r "$_frame_src" ] || _frame_src="$_frame"

  _frame_evidence="$(pub_kv FRAME_EVIDENCE "$_frame_src")"; [ -n "$_frame_evidence" ] || _frame_evidence=UNAVAILABLE
  _frame_at="$(pub_kv FRAME_AT "$_frame_src")"; case "$_frame_at" in ''|*[!0-9]*) _frame_at=0;; esac
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
  if [ "$_workload" = GAME ]; then
    _active=1
    case "$_pkg_source" in *MULTIWINDOW*|*VISIBLE_GAME*) _window=MULTI_WINDOW;; *) _window=FOREGROUND;; esac
  fi
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
  _little_active_min="$(pub_kv LITTLE_ACTIVE_MIN_KHZ "$_snap")"
  _little_active_max="$(pub_kv LITTLE_ACTIVE_MAX_KHZ "$_snap")"
  _big_active_min="$(pub_kv BIG_ACTIVE_MIN_KHZ "$_snap")"
  _big_active_max="$(pub_kv BIG_ACTIVE_MAX_KHZ "$_snap")"
  _gpu_active_min="$(pub_kv GPU_ACTIVE_MIN_HZ "$_snap")"
  _gpu_active_max="$(pub_kv GPU_ACTIVE_MAX_HZ "$_snap")"
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
  _frame_ms="$(pub_kv FRAME_MS "$_frame_src")"; [ -n "$_frame_ms" ] && [ "$_frame_ms" != NA ] || _frame_ms=0
  _fps="$(pub_kv FPS_EST "$_frame_src")"; [ -n "$_fps" ] && [ "$_fps" != NA ] || _fps=0
  _jank="$(pub_kv JANK_PCT "$_frame_src")"; [ -n "$_jank" ] && [ "$_jank" != NA ] || _jank=-1
  _p95="$(pub_kv P95_MS "$_frame_src")"; [ -n "$_p95" ] && [ "$_p95" != NA ] || _p95=0
  _p99="$(pub_kv P99_MS "$_frame_src")"; [ -n "$_p99" ] && [ "$_p99" != NA ] || _p99=0
  _little_mhz="$(pub_khz_mhz "$_little")"
  _big_mhz="$(pub_khz_mhz "$_big")"
  _gpu_mhz="$(pub_hz_mhz "$_gpu")"

  if [ "$_frame_evidence" = VALID ] && [ "$_fps" != 0 ]; then
    _human_frame="Device Truth saat ini membaca sekitar $_fps FPS, jank $_jank persen, p95 $_p95 ms dan p99 $_p99 ms."
  else
    _human_frame="Data frame belum cukup kuat untuk saya jadikan dasar perubahan agresif."
  fi

  _human_thermal=""
  _comfort_pressure=NO
  if [ "$_skin_t" -ge 0 ] 2>/dev/null || [ "$_cpu_t" -ge 0 ] 2>/dev/null || [ "$_gpu_t" -ge 0 ] 2>/dev/null; then
    _human_thermal="Suhu yang terbaca: skin ${_skin_t}C, CPU ${_cpu_t}C, GPU ${_gpu_t}C."
  fi
  if awk -v s="$_skin_t" 'BEGIN{exit !(s>=42)}' 2>/dev/null; then
    _comfort_pressure=YES
    _human_thermal="$_human_thermal Skin sudah masuk comfort pressure untuk preferensi panas pengguna. Saya akan mencari opsi lebih dingin hanya jika kestabilan frame tetap terjaga."
  fi

  _human_power=""
  [ "$_power" -gt 0 ] 2>/dev/null && _human_power="Daya pelepasan baterai sekitar ${_power} mW."

  _human_clock=""
  if [ "$_little_mhz" != NA ] || [ "$_big_mhz" != NA ] || [ "$_gpu_mhz" != NA ]; then
    _human_clock="Clock aktif kira-kira Little ${_little_mhz} MHz, Big ${_big_mhz} MHz, GPU ${_gpu_mhz} MHz."
  fi

  _human_metrics="$_human_frame $_human_thermal $_human_power $_human_clock"

  if [ "$_learn_pkg" = "$_pkg" ]; then
    _lmin="$(pub_kv LITTLE_MIN_KHZ "$_learn")"; [ -n "$_lmin" ] || _lmin=NA
    _lmax="$(pub_kv LITTLE_MAX_KHZ "$_learn")"; [ -n "$_lmax" ] || _lmax=NA
    _bmin="$(pub_kv BIG_MIN_KHZ "$_learn")"; [ -n "$_bmin" ] || _bmin=NA
    _bmax="$(pub_kv BIG_MAX_KHZ "$_learn")"; [ -n "$_bmax" ] || _bmax=NA
    _gmin="$(pub_kv GPU_MIN_HZ "$_learn")"; [ -n "$_gmin" ] || _gmin=NA
    _gmax="$(pub_kv GPU_MAX_HZ "$_learn")"; [ -n "$_gmax" ] || _gmax=NA
  else
    _lmin=NA; _lmax=NA; _bmin=NA; _bmax=NA; _gmin=NA; _gmax=NA
  fi

  _gem="$(pub_kv GEMINI_STATE "$_gem_state")"; [ -n "$_gem" ] || _gem=WAITING
  _gem_conf="$(pub_kv CONFIDENCE "$_gem_prop")"
  case "$_gem_conf" in
    ""|*[!0-9]*) _gem_conf="$(pub_kv GEMINI_CONFIDENCE "$_gem_state")";;
  esac
  case "$_gem_conf" in ""|*[!0-9]*) _gem_conf=0;; esac
  _gem_reason="$(pub_kv REASON "$_gem_prop")"; [ -n "$_gem_reason" ] || _gem_reason="$(pub_kv GEMINI_DETAIL "$_gem_state")"
  _gem_thought="$(pub_kv GEMINI_THOUGHT "$_gem_state")"
  _gem_thought_at="$(pub_kv GEMINI_THOUGHT_AT "$_gem_state")"; case "$_gem_thought_at" in ''|*[!0-9]*) _gem_thought_at=0;; esac
  _gem_thought_pkg="$(pub_kv GEMINI_THOUGHT_PACKAGE "$_gem_state")"; [ -n "$_gem_thought_pkg" ] || _gem_thought_pkg=UNKNOWN
  _gem_verdict="$(pub_kv GEMINI_VERDICT "$_gem_state")"; [ -n "$_gem_verdict" ] || _gem_verdict=UNKNOWN
  _gem_reason_token="$(pub_kv GEMINI_REASON_TOKEN "$_gem_state")"; [ -n "$_gem_reason_token" ] || _gem_reason_token="$_gem_reason"
  _gem_guard_sec="$(pub_kv GEMINI_GUARD_SEC "$_gem_state")"; [ -n "$_gem_guard_sec" ] || _gem_guard_sec=NA
  _gem_guard_reason="$(pub_kv GEMINI_GUARD_REASON "$_gem_state")"; [ -n "$_gem_guard_reason" ] || _gem_guard_reason=NA
  _gem_last_success_age="$(pub_kv GEMINI_LAST_SUCCESS_AGE_SEC "$_gem_state")"; [ -n "$_gem_last_success_age" ] || _gem_last_success_age=NA
  _hlocal="$(pub_kv HERMES_LOCAL_STATE "$_hermes_state")"; [ -n "$_hlocal" ] || _hlocal=WAITING
  _hcloud="$(pub_kv HERMES_CLOUD_STATE "$_hermes_state")"; [ -n "$_hcloud" ] || _hcloud=STANDBY
  _hroute="$(pub_kv HERMES_CLOUD_ROUTE "$_hermes_state")"; [ -n "$_hroute" ] || _hroute=LOCAL
  _hmodel="$(pub_kv HERMES_CLOUD_MODEL "$_hermes_state")"; [ -n "$_hmodel" ] || _hmodel=NA
  _hhttp="$(pub_kv HERMES_CLOUD_HTTP "$_hermes_state")"; [ -n "$_hhttp" ] || _hhttp=NA
  _hauth="$(pub_kv HERMES_CLOUD_AUTH "$_hermes_state")"; [ -n "$_hauth" ] || _hauth=UNKNOWN
  _hreason="$(pub_kv HERMES_CLOUD_DETAIL "$_hermes_state")"; [ -n "$_hreason" ] || _hreason=NO_REVIEW_YET
  _hmode="$(pub_kv HERMES_MODE "$_hermes_state")"; [ -n "$_hmode" ] || _hmode=DEPUTY_STANDBY
  _hactive="$(pub_kv HERMES_ACTIVE_SOURCE "$_hermes_state")"; [ -n "$_hactive" ] || _hactive=NONE
  _hcloud_used="$(pub_kv HERMES_CLOUD_USED "$_hermes_state")"; [ -n "$_hcloud_used" ] || _hcloud_used=NO
  _hcloud_active="$(pub_kv HERMES_CLOUD_ACTIVE "$_hermes_state")"; [ -n "$_hcloud_active" ] || _hcloud_active=NO
  _hcloud_last_age="$(pub_kv HERMES_CLOUD_LAST_SUCCESS_AGE_SEC "$_hermes_state")"; [ -n "$_hcloud_last_age" ] || _hcloud_last_age=NA
  _hcloud_last_route="$(pub_kv HERMES_CLOUD_LAST_ROUTE "$_hermes_state")"; [ -n "$_hcloud_last_route" ] || _hcloud_last_route=NA
  _hcloud_last_model="$(pub_kv HERMES_CLOUD_LAST_MODEL "$_hermes_state")"; [ -n "$_hcloud_last_model" ] || _hcloud_last_model=NA
  _hcloud_last_verdict="$(pub_kv HERMES_CLOUD_LAST_VERDICT "$_hermes_state")"; [ -n "$_hcloud_last_verdict" ] || _hcloud_last_verdict=NA
  _hconf="$(pub_kv CONFIDENCE "$_local_vote")"; case "$_hconf" in ''|*[!0-9]*) _hconf=0;; esac
  _cons_state="$(pub_kv CONSENSUS_STATE "$_cons")"; [ -n "$_cons_state" ] || _cons_state=OBSERVING
  _active_brain_source="$(pub_kv ACTIVE_BRAIN_SOURCE "$_cons")"; [ -n "$_active_brain_source" ] || _active_brain_source=NONE
  _shadow_state="$(pub_kv SHADOW_STATE "$_shadow")"; [ -n "$_shadow_state" ] || _shadow_state=WAITING
  _shadow_n="$(pub_kv SHADOW_WINDOWS "$_shadow")"; case "$_shadow_n" in ''|*[!0-9]*) _shadow_n=0;; esac
  _exec_state="$(pub_kv EXECUTOR_STATE "$_execution")"; [ -n "$_exec_state" ] || _exec_state=IDLE
  _exec_reason="$(pub_kv EXECUTOR_REASON "$_execution")"; [ -n "$_exec_reason" ] || _exec_reason=WAITING
  _exec_intent="$(pub_kv APPLIED_INTENT "$_execution")"; [ -n "$_exec_intent" ] || _exec_intent=NONE
  _exec_actuators="$(pub_kv APPLIED_ACTUATORS "$_execution")"; [ -n "$_exec_actuators" ] || _exec_actuators=NONE
  _exec_little="$(pub_kv APPLIED_LITTLE "$_execution")"; [ -n "$_exec_little" ] || _exec_little=NA
  _exec_big="$(pub_kv APPLIED_BIG "$_execution")"; [ -n "$_exec_big" ] || _exec_big=NA
  _exec_gpu="$(pub_kv APPLIED_GPU "$_execution")"; [ -n "$_exec_gpu" ] || _exec_gpu=NA
  _readback="$(pub_kv READBACK "$_execution")"; [ -n "$_readback" ] || _readback=NA
  _rollback="$(pub_kv ROLLBACK_STATE "$_execution")"; [ -n "$_rollback" ] || _rollback=STANDBY
  _railway_state="$(pub_kv RAILWAY_STATE "$_railway")"; [ -n "$_railway_state" ] || _railway_state=WAITING
  _migration_state="$(pub_kv MIGRATION_STATE "$_migration")"; [ -n "$_migration_state" ] || _migration_state=UNKNOWN
  _credential_count="$(pub_kv CREDENTIAL_FILE_COUNT "$_migration")"; case "$_credential_count" in ''|*[!0-9]*) _credential_count=0;; esac
  # Neurons is DJAEGER's current-day Hermes Cloud usage ledger, not provider quota.
  # It resets at 00:00 UTC / 07:00 WIB and only successful Cloud inference increments it.
  # Publisher must never expose yesterday's ledger just because Hermes Cloud has
  # not been invoked since rollover. Normalize stale UTC-day state here too.
  _neuron_day="$(pub_kv UTC_DAY "$_neuron")"
  _neuron_today="$(date -u +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)"
  if [ -n "$_neuron_day" ] && [ "$_neuron_day" != "$_neuron_today" ]; then
    _ntmp="$_neuron.tmp.$PPID"
    {
      echo "SCHEMA=DJAEGER_NEURON_LIVE_V1"
      echo "UTC_DAY=$_neuron_today"
      echo "RESET_AT=00:00_UTC"
      echo "RESET_AT_WIB=07:00"
      echo "USED_EST=0"
      echo "LIMIT=10000"
      echo "FAST_CALLS=0"
      echo "SMART_CALLS=0"
      echo "DEEP_CALLS=0"
      echo "SUCCESS_CALLS=0"
      echo "LAST_DELTA=0"
      echo "METHOD=DAILY_ROLLOVER_PUBLISHER"
      echo "ESTIMATED=YES"
      echo "SOURCE=LIVE_SUCCESSFUL_HERMES_CLOUD_ONLY"
      echo "UPDATED_AT=$(date +%s)"
    } > "$_ntmp"
    chmod 600 "$_ntmp" 2>/dev/null
    mv -f "$_ntmp" "$_neuron"
  fi
  _neuron_used="$(pub_kv USED_EST "$_neuron")"
  _neuron_limit="$(pub_kv LIMIT "$_neuron")"
  case "$_neuron_used" in ''|*[!0-9]*) _neuron_used=0;; esac
  case "$_neuron_limit" in ''|*[!0-9]*) _neuron_limit=10000;; esac
  _neuron_tier=LIVE_DAILY_HERMES_CLOUD_USAGE

  _gem_count=$(sed -n 's/^KEY_[1-4]=//p' "$_gem_vault" 2>/dev/null | awk 'NF{n++}END{print n+0}')
  case "$_gem_count" in ''|*[!0-9]*) _gem_count=0;; esac
  _now=$(date +%s); _gem_ready=0; _gem_cd=0; _i=1
  while [ "$_i" -le "$_gem_count" ]; do
    _until="$(pub_kv "KEY_${_i}_UNTIL" "$_gem_cooldown")"; case "$_until" in ''|*[!0-9]*) _until=0;; esac
    if [ "$_until" -gt "$_now" ] 2>/dev/null; then _gem_cd=$((_gem_cd+1)); else _gem_ready=$((_gem_ready+1)); fi
    _i=$((_i+1))
  done
  _gem_http="$(pub_kv GEMINI_HTTP "$_gem_state")"; [ -n "$_gem_http" ] || _gem_http=NA
  _gem_age="$(pub_age_sec "$_gem_state" UPDATED_AT)"
  _gem_prop_age="$(pub_age_sec "$_gem_prop" AT)"
  _local_vote_age="$(pub_age_sec "$_local_vote" AT)"
  _cloud_vote_age="$(pub_age_sec "$_cloud_vote" AT)"
  _hermes_age="$(pub_age_sec "$_hermes_state" UPDATED_AT)"
  _cons_age="$(pub_age_sec "$_cons" UPDATED_AT)"
  _shadow_age="$(pub_age_sec "$_shadow" UPDATED_AT)"
  _exec_age="$(pub_age_sec "$_execution" UPDATED_AT)"
  _rail_age="$(pub_age_sec "$_railway" UPDATED_AT)"

  _gem_connection=WAITING
  if [ "$_gem_count" -eq 0 ]; then _gem_connection=NOT_CONFIGURED
  else
    case "$_gem_http:$_gem" in
      200:*) _gem_connection=ONLINE ;;
      429:*|*:COOLDOWN|*:ALL_KEYS_COOLDOWN) _gem_connection=COOLDOWN ;;
      401:*|403:*) _gem_connection=AUTH_ERROR ;;
      000:*|NA:HTTP_ERROR|*:UNAVAILABLE) _gem_connection=OFFLINE ;;
      *) _gem_connection=READY ;;
    esac
  fi

  [ "$_gem_age" -le 180 ] 2>/dev/null || _gem_connection=STALE

  _h_access="$(pub_kv HERMES_ACCESS_KEY "$_hermes_cfg")"
  if [ -n "$_h_access" ]; then
    [ "$_hauth" = UNKNOWN ] && _hauth=CONFIGURED
  else
    _hauth=NOT_CONFIGURED
  fi
  unset _h_access
  _hermes_cloud_connection=WAITING
  case "$_hcloud" in
    ONLINE|APPROVED|REJECTED|TAKEOVER_READY|OBSERVE) _hermes_cloud_connection=ONLINE ;;
    REACHABLE_IDLE) _hermes_cloud_connection=REACHABLE ;;
    NO_KEY) _hermes_cloud_connection=NOT_CONFIGURED ;;
    AUTH_ERROR) _hermes_cloud_connection=AUTH_ERROR ;;
    HTTP_ERROR|UNAVAILABLE|OFFLINE) _hermes_cloud_connection=OFFLINE ;;
    *) [ "$_hauth" = NOT_CONFIGURED ] && _hermes_cloud_connection=NOT_CONFIGURED ;;
  esac
  _hermes_connection="$_hermes_cloud_connection"
  case "$_hlocal" in
    TAKEOVER_LOCAL|TAKEOVER_LOCAL_SYNTH|TAKEOVER_CLOUD|ASSIMILATED_GEMINI|VALIDATED_CANDIDATE|OBSERVE|DEPUTY_STANDBY)
      _hermes_connection=ONLINE ;;
  esac
  [ "$_hermes_age" -le 180 ] 2>/dev/null || { _hermes_connection=STALE; _hermes_cloud_connection=STALE; }

  _module_code=$(sed -n 's/^versionCode=//p' "${MODDIR:-/data/adb/modules/djaeger_ai_observer}/module.prop" 2>/dev/null | head -n1)
  case "$_module_code" in ''|*[!0-9]*) _module_code=0;; esac
  _apk_ver="$(pub_kv APK_VERSION_CODE "$_handshake")"
  _expected_apk="$(pub_kv EXPECTED_APK_VERSION_CODE "$_handshake")"; [ -n "$_expected_apk" ] || _expected_apk=111
  _hand_schema="$(pub_kv SCHEMA "$_handshake")"
  _ack_id="$(pub_kv ACK_ID "$_handshake")"
  _ack_at="$(pub_kv ACK_AT "$_handshake")"; case "$_ack_at" in ''|*[!0-9]*) _ack_at=0;; esac
  _hand_age=$((_now-_ack_at)); [ "$_hand_age" -ge 0 ] 2>/dev/null || _hand_age=999999
  _pair="$(pub_kv PAIR_VERIFIED "$_handshake")"
  [ "$_pair" = YES ] && [ "$_hand_schema" = DJAEGER_AI_ADAPTIVE_V3 ] && [ "$_hand_age" -le 86400 ] 2>/dev/null || _pair=NO
  _generation=$(cat "$_genfile" 2>/dev/null | head -n1); case "$_generation" in ''|*[!0-9]*) _generation=0;; esac
  _generation=$((_generation+1))
  _gen_tmp="$(mktemp "${_genfile}.tmp.XXXXXX" 2>/dev/null)"
  [ -n "$_gen_tmp" ] || _gen_tmp="${_genfile}.tmp.${_now}.${_generation}"
  printf '%s\n' "$_generation" > "$_gen_tmp"; chmod 600 "$_gen_tmp" 2>/dev/null; mv -f "$_gen_tmp" "$_genfile"

  _cloud_connection="GEMINI_$_gem_connection|HERMES_$_hermes_connection"

  # Brain plan truth. Gemini is primary; ONE HERMES is deputy takeover.
  _plan_provider=NONE
  _plan_intent=NONE
  _plan_actuators=NONE
  _cloud_plan_state=NOT_USED
  _cloud_plan_score=0
  _cloud_plan_reason=NO_ACTIVE_BRAIN_PLAN
  if [ -r "$_candidate" ] && [ "$(pub_kv PACKAGE "$_candidate")" = "$_pkg" ]; then
    _plan_provider="$(pub_kv BRAIN_SOURCE "$_candidate")"; [ -n "$_plan_provider" ] || _plan_provider=UNKNOWN
    _plan_intent="$(pub_kv INTENT "$_candidate")"; [ -n "$_plan_intent" ] || _plan_intent=FRAME_FIRST_BALANCED
    _plan_actuators="$(pub_kv ACTUATORS "$_candidate")"; [ -n "$_plan_actuators" ] || _plan_actuators=ALL
    _cloud_plan_state=PROPOSED
    _cloud_plan_score="$(pub_kv CONFIDENCE "$_candidate")"; case "$_cloud_plan_score" in ''|*[!0-9]*) _cloud_plan_score=0;; esac
    case "$_plan_provider" in
      GEMINI) _cloud_plan_reason="$_gem_reason" ;;
      HERMES_LOCAL|HERMES_CLOUD|HERMES_H2) _cloud_plan_reason="$(pub_kv REASON "$_hermes_plan")"; [ -n "$_cloud_plan_reason" ] || _cloud_plan_reason="$_hreason" ;;
      *) _cloud_plan_reason=UNKNOWN_SOURCE ;;
    esac
    [ "$_cons_state" = PENDING_SHADOW ] && _cloud_plan_state=ACCEPTED_FOR_SHADOW
    [ "$_shadow_state" = PASS ] && _cloud_plan_state=SHADOW_PASS
    [ "$_exec_state" = APPLIED ] && _cloud_plan_state=APPLIED_BY_AI_AGENT
    [ "$_exec_state" = ROLLED_BACK ] && _cloud_plan_state=ROLLED_BACK_BY_AI_AGENT
    [ "$_exec_state" = ROLLBACK_FAILED ] && _cloud_plan_state=ROLLBACK_FAILED
  elif [ "$_active_brain_source" = GEMINI ]; then
    _plan_provider=GEMINI
    _cloud_plan_state=OBSERVE
    _cloud_plan_reason=PRIMARY_ONLINE_NO_CHANGE
  elif [ "$_hmode" = TAKEOVER ] || [ "$_hmode" = TAKEOVER_CLOUD_ESCALATED ]; then
    _plan_provider=HERMES_H2
    _cloud_plan_state=OBSERVE
    _cloud_plan_reason="$_hreason"
  fi

  _cap_count=0
  for _path_key in LITTLE_POLICY_PATH BIG_POLICY_PATH GPU_DEVFREQ_PATH; do
    _cap_path="$(pub_kv "$_path_key" "$_snap")"
    [ -n "$_cap_path" ] && [ "$_cap_path" != NA ] && _cap_count=$((_cap_count+1))
  done
  _actuator_truth=UNVERIFIED
  _action_count=0
  if [ "$_exec_state" = APPLIED ] && [ "$_readback" = VERIFIED ]; then _actuator_truth=6; _action_count=6; fi

  _bug_health=OK; _bug_open=NO; _bug_severity=INFO; _bug_component=NONE; _bug_code=NONE
  _bug_summary="No open verified runtime fault"
  _bug_facts="executor=$_exec_state readback=$_readback rollback=$_rollback"
  _bug_action=NONE; _bug_recovery=$_rollback
  if [ "$_rollback" = RESTORE_FAILED ] || [ "$_exec_state" = ROLLBACK_FAILED ]; then
    _bug_health=ERROR; _bug_open=YES; _bug_severity=CRITICAL; _bug_component=LOCAL_EXECUTOR; _bug_code=RESTORE_FAILED
    _bug_summary="Pre-apply CPU/GPU bounds could not be fully restored"
    _bug_action="Execution remains fail-closed and the recovery backup is preserved"
  elif [ "$_seq" -gt 10 ] 2>/dev/null && [ "$_exec_age" -gt 10 ] 2>/dev/null; then
    _bug_health=ERROR; _bug_open=YES; _bug_severity=HIGH; _bug_component=LOCAL_EXECUTOR; _bug_code=EXECUTOR_STALE
    _bug_summary="Local executor state is stale while observer is alive"
    _bug_action="Block adaptive execution until executor state is fresh"
  elif [ "$_exec_state" = ROLLED_BACK ]; then
    _bug_health=RECOVERED; _bug_open=NO; _bug_severity=INFO; _bug_component=LOCAL_EXECUTOR; _bug_code=ROLLBACK_COMPLETE
    _bug_summary="Adaptive execution was rolled back by a local gate"
    _bug_action="Continue observing before any new approval"
  fi

  case "$_plan_intent" in
    FRAME_RECOVERY)
      _intent_human="Fokus saya sekarang memulihkan konsistensi frame terlebih dahulu; penghematan daya hanya boleh mengikuti jika frame tidak memburuk."
      ;;
    POWER_EFFICIENCY)
      _intent_human="Frame terlihat cukup aman, jadi saya mencoba mencari titik daya yang lebih rendah tanpa mengorbankan kelancaran."
      ;;
    PROVEN_REUSE)
      _intent_human="Saya memilih pola yang sudah pernah terbukti pada perangkat ini daripada menebak batas baru."
      ;;
    FRAME_FIRST_BALANCED)
      _intent_human="Saya menyeimbangkan clock seperlunya dengan prioritas utama kestabilan frame, bukan mengejar frekuensi setinggi mungkin."
      ;;
    *)
      _intent_human="Saya belum mengunci diri ke profil tetap; keputusan tetap mengikuti telemetry dan hasil belajar perangkat."
      ;;
  esac

  # Dynamic THOUGHT follows the actual brain hierarchy and Agent outcome.
  _thought_source=OBSERVER_LOCAL
  _thought_status=OBSERVING
  _thought_age=$((_now-_epoch)); [ "$_thought_age" -ge 0 ] 2>/dev/null || _thought_age=999999
  _thought_conf="$_confidence"
  _thought_reason=MEASURED_DEVICE
  _thought_evidence="telemetry=$_seq frame=$_frame_evidence learning=$_learning samples=$_samples"
  _thought="AI Agent mengumpulkan Device Truth untuk $_pkg. Tujuan tetap: kestabilan frame sebagai kenyamanan visual, suhu serendah mungkin sebagai kenyamanan fisik, lalu daya minimum tanpa merusak keduanya."

  case "$_active_brain_source" in
    GEMINI)
      _thought_source=GEMINI
      _thought_conf="$_gem_conf"
      _thought_reason="${_gem_reason_token:-$_gem_reason}"
      _gt_age=$((_now-_gem_thought_at)); [ "$_gt_age" -ge 0 ] 2>/dev/null || _gt_age=999999
      if [ "$_gem_thought_pkg" = "$_pkg" ] && [ "$_gt_age" -le 180 ] 2>/dev/null && [ -n "$_gem_thought" ]; then
        case "$_gem_verdict" in CANDIDATE) _thought_status=PRIMARY_CANDIDATE;; *) _thought_status=PRIMARY_OBSERVE;; esac
        _thought_evidence="brain=GEMINI role=PRIMARY verdict=$_gem_verdict reason=$_thought_reason"
        _thought="$_gem_thought"
        _thought_age="$_gt_age"
      elif [ -r "$_gem_prop" ]; then
        _thought_status=PRIMARY_CANDIDATE
        _thought_evidence="brain=GEMINI role=PRIMARY proposal=CANDIDATE reason=$_thought_reason"
        _thought="Gemini melihat kandidat yang layak diuji, tetapi belum menganggapnya sebagai hasil akhir. Kandidat tetap harus melewati ONE HERMES review, shadow, safety gate, dan readback lokal."
      else
        _thought_status=PRIMARY_OBSERVE
        _thought_evidence="brain=GEMINI role=PRIMARY proposal=NONE reason=$_thought_reason"
        _thought="Gemini menilai evidence saat ini belum cukup untuk membenarkan perubahan hardware. Saya tetap mengamati sampai ada pola yang cukup kuat untuk keputusan baru."
      fi
      ;;
    HERMES_LOCAL)
      _thought_source=HERMES_H2
      _thought_conf="$_hconf"
      _thought_reason="$_hreason"
      if [ "$_hlocal" = TAKEOVER_THERMAL_HOLD ]; then
        _thought_status=DEPUTY_THERMAL_HOLD
        _thought_evidence="brain=ONE_HERMES source=LOCAL comfort=HARD_THERMAL_HOLD gemini=$_gem frame=$_frame_evidence"
        _thought="Hard thermal gate sedang aktif, jadi ONE HERMES sengaja menahan transaksi hardware baru dan memberi kontrol thermal native ruang bekerja. Setelah gate lepas, frame dinilai lebih dulu sebelum strategi baru dipertimbangkan."
      elif [ "$_hlocal" = TAKEOVER_LOCAL_SYNTH ]; then
        _thought_status=DEPUTY_LOCAL_SYNTH
        _thought_evidence="brain=ONE_HERMES source=LOCAL synthesis=KNOWLEDGE_DRIVEN intent=$_plan_intent gemini=$_gem frame=$_frame_evidence"
        _thought="Gemini sedang tidak tersedia, jadi ONE HERMES Local menyusun kandidat dari evidence perangkat dan memory yang sudah dipelajari. Ini bukan profil tetap; kandidat tetap harus lolos shadow, safety, readback, dan outcome."
      elif [ "$_hlocal" = TAKEOVER_LOCAL ]; then
        _thought_status=DEPUTY_LOCAL_TAKEOVER
        _thought_evidence="brain=ONE_HERMES source=LOCAL synthesis=PROVEN_REUSE intent=$_plan_intent gemini=$_gem"
        _thought="Gemini sedang cooldown, jadi ONE HERMES Local menjaga continuity dengan pengetahuan yang sudah terbukti. Saya tidak membuat batas baru hanya demi terlihat aktif."
      else
        _thought_status=DEPUTY_LOCAL_OBSERVE
        _thought_evidence="brain=ONE_HERMES source=LOCAL synthesis=NONE reason=$_hreason gemini=$_gem frame=$_frame_evidence"
        _thought="Gemini belum tersedia dan ONE HERMES Local sedang menjaga continuity. Belum ada manfaat terukur yang cukup untuk menyentuh hardware, jadi saya mempertahankan kondisi sekarang sambil menunggu evidence baru."
      fi
      ;;
    HERMES_CLOUD)
      _thought_source=HERMES_H2
      _thought_status=DEPUTY_CLOUD_TAKEOVER
      _thought_conf="$_cloud_plan_score"
      _thought_reason="$_hreason"
      _thought_evidence="brain=ONE_HERMES source=CLOUD route=$_hroute model=$_hmodel cloud_used=$_hcloud_used"
      _thought="Pengetahuan lokal belum cukup meyakinkan, jadi ONE HERMES meminta bantuan cognition Cloud untuk menilai strategi. Cloud tetap tidak memiliki otoritas hardware; keputusan akhir harus melewati gate lokal."
      ;;
    HERMES_H2)
      _thought_source=HERMES_H2
      _thought_status=DEPUTY_OBSERVE
      _thought_reason="$_hreason"
      _thought_evidence="brain=ONE_HERMES mode=$_hmode"
      _thought="Gemini tidak tersedia, sehingga ONE HERMES bertugas sebagai deputy. Belum ada alasan terukur untuk mengubah hardware, jadi kondisi sekarang dipertahankan."
      ;;
  esac

  # ONE_HERMES_THOUGHT_PUBLISHER_V1
  # Publisher is display-only. The ONE HERMES THOUGHT process owns reasoning text.
  case "$_hactive" in
    HERMES_LOCAL|HERMES_H2|HERMES_CLOUD)
      _ht="$_root/runtime/hermes_thought.env"
      if [ -r "$_ht" ]; then
        _ht_ver="$(pub_kv WORKER_VERSION "$_ht")"
        _ht_at="$(pub_kv AT "$_ht")"; case "$_ht_at" in ''|*[!0-9]*) _ht_at=0;; esac
        _ht_age=$((_now-_ht_at)); [ "$_ht_age" -ge 0 ] 2>/dev/null || _ht_age=999999
        _ht_pkg="$(pub_kv PACKAGE "$_ht")"
        _ht_text="$(pub_kv TEXT "$_ht")"
        if [ "$_ht_ver" = ONE_HERMES_THOUGHT_V3_4 ] && [ "$_ht_pkg" = "$_pkg" ] && [ "$_ht_age" -le 180 ] 2>/dev/null && [ -n "$_ht_text" ]; then
          _thought_source=HERMES_H2
          _thought_status="$(pub_kv STATUS "$_ht")"; [ -n "$_thought_status" ] || _thought_status=DEPUTY_LOCAL_OBSERVE
          _thought_conf="$(pub_kv CONFIDENCE "$_ht")"; case "$_thought_conf" in ''|*[!0-9]*) _thought_conf=0;; esac
          _thought_reason="$(pub_kv REASON "$_ht")"; [ -n "$_thought_reason" ] || _thought_reason=ONE_HERMES_LOCAL_REASONING
          _thought_evidence="$(pub_kv EVIDENCE "$_ht")"
          _thought="$_ht_text"
          _thought_age="$_ht_age"
        fi
      fi
      ;;
  esac

  if [ "$_cons_state" = PENDING_SHADOW ]; then
    _thought_status=PENDING_SHADOW
    _thought="$_thought Kandidat ini sekarang masuk shadow test. Saya sedang memeriksa apakah perubahan benar-benar menjaga frame dan hanya menurunkan daya bila kestabilannya tetap aman."
  fi
  if [ "$_shadow_state" = PASS ]; then
    _thought_status=SHADOW_PASS
    _thought="$_thought Shadow baru saja lulus, tetapi ini belum sukses akhir. AI Agent baru boleh mencoba transaksi lokal yang terikat digest; saya masih menunggu exact readback serta hasil frame dan daya sesudah penerapan."
  fi
  if [ "$_exec_state" = APPLIED ] && [ "$_readback" = VERIFIED ]; then
    _thought_source=AI_AGENT
    _thought_status=APPLIED_VERIFIED
    _thought_age="$_exec_age"
    _thought_reason="$_exec_reason"
    _thought_evidence="little=$_exec_little big=$_exec_big gpu=$_exec_gpu readback=$_readback"
    _thought="Keputusan dari $_active_brain_source sudah diterapkan oleh AI Agent dan readback cocok: Little $_exec_little, Big $_exec_big, GPU $_exec_gpu. $_human_frame $_human_thermal Sekarang saya belum menyebutnya berhasil; saya masih membandingkan frame dan daya untuk menentukan KEEP atau ROLLBACK."
  elif [ "$_exec_state" = ROLLED_BACK ]; then
    _thought_source=AI_AGENT
    _thought_status=ROLLED_BACK
    _thought_age="$_exec_age"
    _thought_reason="$_exec_reason"
    _thought_evidence="rollback=$_rollback readback=$_readback"
    _thought="Saya membatalkan strategi tadi karena $_exec_reason. Hardware sudah dikembalikan ke state sebelumnya, dan kegagalan ini menjadi evidence baru agar keputusan berikutnya tidak mengulangi pola yang sama."
  elif [ "$_exec_state" = ROLLBACK_FAILED ]; then
    _thought_source=AI_AGENT
    _thought_status=ROLLBACK_FAILED
    _thought_age="$_exec_age"
    _thought_conf=0
    _thought_reason="$_exec_reason"
    _thought_evidence="rollback=$_rollback readback=$_readback"
    _thought="Saya menghentikan eksekusi karena recovery SYSFS belum bisa dibuktikan aman. Saya tidak akan memaksakan write baru selama readback belum jelas; keselamatan state perangkat lebih penting daripada terus mencoba kandidat."
  fi
  _thought_fresh=0; [ "$_thought_age" -le 180 ] 2>/dev/null && _thought_fresh=1

  if [ -r "$_root/history/telemetry.csv" ]; then _history_bytes="$(wc -c < "$_root/history/telemetry.csv" 2>/dev/null)"
  else _history_bytes=0
  fi
  case "$_history_bytes" in ''|*[!0-9]*) _history_bytes=0;; esac
  _memory_used_bytes=0
  for _mf in "$_root/history/"*; do
    [ -f "$_mf" ] || continue
    _mb="$(wc -c < "$_mf" 2>/dev/null)"; case "$_mb" in ''|*[!0-9]*) _mb=0;; esac
    _memory_used_bytes=$((_memory_used_bytes+_mb))
  done
  _thought_knowledge_rows=0
  if [ -r "$_root/history/hermes_thought_knowledge.tsv" ]; then
    _thought_knowledge_rows="$(awk 'NR>1{n++}END{print n+0}' "$_root/history/hermes_thought_knowledge.tsv" 2>/dev/null)"
  fi
  _reject_knowledge_rows=0
  if [ -r "$_root/history/shadow_reject_strategies.csv" ]; then
    _reject_knowledge_rows="$(awk 'NR>1{n++}END{print n+0}' "$_root/history/shadow_reject_strategies.csv" 2>/dev/null)"
  fi
  case "$_thought_knowledge_rows" in ''|*[!0-9]*) _thought_knowledge_rows=0;; esac
  case "$_reject_knowledge_rows" in ''|*[!0-9]*) _reject_knowledge_rows=0;; esac
  _knowledge_rows=$((_samples+_thought_knowledge_rows+_reject_knowledge_rows))

  _outcome_rows=0; _outcome_keep=0; _outcome_rollback=0; _outcome_rollback_failed=0
  _recent_outcome_rows=0; _recent_keep=0; _recent_rollback=0; _recent_rollback_failed=0
  _validation_outcome_rows=0; _validation_keep=0; _validation_rollback=0; _validation_rollback_failed=0; _validation_superseded_drift=0
  _outcome_last=NONE; _outcome_reason=NONE
  if [ -r "$_outcomes" ]; then
    _outcome_rows="$(awk -F, 'NR>1{n++}END{print n+0}' "$_outcomes" 2>/dev/null)"
    _outcome_keep="$(awk -F, 'NR>1&&$4=="KEPT"{n++}END{print n+0}' "$_outcomes" 2>/dev/null)"
    _outcome_rollback="$(awk -F, 'NR>1&&($4=="ROLLED_BACK"||$4=="ROLLBACK_FAILED"){n++}END{print n+0}' "$_outcomes" 2>/dev/null)"
    _outcome_rollback_failed="$(awk -F, 'NR>1&&$4=="ROLLBACK_FAILED"{n++}END{print n+0}' "$_outcomes" 2>/dev/null)"
    _outcome_last="$(awk -F, 'NR>1{v=$4}END{print v}' "$_outcomes" 2>/dev/null)"; [ -n "$_outcome_last" ] || _outcome_last=NONE
    _outcome_reason="$(awk -F, 'NR>1{v=$5}END{print v}' "$_outcomes" 2>/dev/null)"; [ -n "$_outcome_reason" ] || _outcome_reason=NONE

    _maturity_pkg="$_learn_pkg"; [ -n "$_maturity_pkg" ] || _maturity_pkg="$_pkg"
    _recent="$(awk -F, -v p="$_maturity_pkg" '
      NR>1&&$2==p { d[++n]=$3; r[n]=$4; q[n]=$5 }
      END {
        s=n-9; if(s<1)s=1;
        for(i=s;i<=n;i++){
          total++;
          if(r[i]=="KEPT") keep++;
          if(r[i]=="ROLLED_BACK"||r[i]=="ROLLBACK_FAILED") rb++;
          if(r[i]=="ROLLBACK_FAILED") rbf++;
        }
        printf "%d %d %d %d\n", total+0, keep+0, rb+0, rbf+0
      }' "$_outcomes" 2>/dev/null)"
    set -- $_recent
    _recent_outcome_rows="${1:-0}"
    _recent_keep="${2:-0}"
    _recent_rollback="${3:-0}"
    _recent_rollback_failed="${4:-0}"

    _validation="$(awk -F, -v p="$_maturity_pkg" '
      NR>1&&$2==p { d[++n]=$3; r[n]=$4; q[n]=$5 }
      END {
        s=n-9; if(s<1)s=1;
        for(i=s;i<=n;i++){
          total++;
          superseded=0;
          recovered=0;
          if(r[i]=="ROLLBACK_FAILED"){
            for(j=i+1;j<=n;j++){
              if(d[j]==d[i] && r[j]=="RELEASED" && q[j] ~ /EXTERNAL_OVERRIDE/){
                superseded=1; break;
              }
              if(d[j]==d[i] && r[j]=="ROLLED_BACK" && q[j] ~ /READBACK_RECOVERED/){
                recovered=1; break;
              }
            }
          }
          if(recovered){
            continue;
          }
          if(superseded){
            sup++;
            if(q[i]!="SYSFS_DRIFT") rb++;
            continue;
          }
          if(r[i]=="KEPT") keep++;
          if(r[i]=="ROLLED_BACK"||r[i]=="ROLLBACK_FAILED") rb++;
          if(r[i]=="ROLLBACK_FAILED") rbf++;
        }
        printf "%d %d %d %d %d\n", total+0, keep+0, rb+0, rbf+0, sup+0
      }' "$_outcomes" 2>/dev/null)"
    set -- $_validation
    _validation_outcome_rows="${1:-0}"
    _validation_keep="${2:-0}"
    _validation_rollback="${3:-0}"
    _validation_rollback_failed="${4:-0}"
    _validation_superseded_drift="${5:-0}"
  fi
  case "$_outcome_rows" in ''|*[!0-9]*) _outcome_rows=0;; esac
  case "$_outcome_keep" in ''|*[!0-9]*) _outcome_keep=0;; esac
  case "$_outcome_rollback" in ''|*[!0-9]*) _outcome_rollback=0;; esac
  case "$_outcome_rollback_failed" in ''|*[!0-9]*) _outcome_rollback_failed=0;; esac
  # Permanent readiness belongs to the learned game model, not to the
  # app that happens to be foreground when Control Center publishes.
  _maturity_learning="$(pub_kv STATE "$_learn")"; [ -n "$_maturity_learning" ] || _maturity_learning=WAITING
  _maturity_samples="$(pub_kv SAMPLES "$_learn")"; case "$_maturity_samples" in ''|*[!0-9]*) _maturity_samples=0;; esac
  _maturity_confidence="$(pub_kv CONFIDENCE "$_learn")"; case "$_maturity_confidence" in ''|*[!0-9]*) _maturity_confidence=0;; esac

  _permanent_readiness=LEARNING
  if [ "$_maturity_learning" = READY_HARDWARE_MODEL ] && [ "$_maturity_samples" -ge 1000 ] 2>/dev/null && [ "$_maturity_confidence" -ge 90 ] 2>/dev/null; then
    _permanent_readiness=LIVE_VALIDATION_REQUIRED
    if [ "$_validation_keep" -ge 5 ] 2>/dev/null && [ "$_validation_rollback_failed" -eq 0 ] 2>/dev/null && [ "$_validation_keep" -gt "$_validation_rollback" ] 2>/dev/null; then
      _permanent_readiness=MATURE_CANDIDATE
    fi
  fi
  _exec_mode="$(cat "$_root/config/execution_mode" 2>/dev/null | head -n1)"; [ -n "$_exec_mode" ] || _exec_mode=AUTO
  _runtime_profile=LEARNED_PENDING; [ "$_exec_state" = APPLIED ] && _runtime_profile=ADAPTIVE_LEARNED
  _tel="$_epoch,$_cpu_t,$_gpu_t,$_skin_t,$_bat_t,$_little,$_big,$_gpu,$_runtime_profile,$_frame_ms,$_fps,$_jank,$_p95,$_p99,0,$_battery_status,$_current,$_voltage,$_power,$_power_valid,$_power_reason,$_pkg,$_window"
  _frame_epoch="$_epoch"
  [ "$_frame_at" -gt 0 ] 2>/dev/null && _frame_epoch="$_frame_at"
  _frame_line="$_frame_epoch,$_runtime_profile,$_frame_ms,$_fps,$_jank,$_p95,$_p99"
  _plan_line=""
  if [ -r "$_candidate" ]; then
    _pc="$(pub_kv CONFIDENCE "$_candidate")"; [ -n "$_pc" ] || _pc=0
    _plmin="$(pub_kv LITTLE_MIN_KHZ "$_candidate")"; _plmax="$(pub_kv LITTLE_MAX_KHZ "$_candidate")"
    _pbmin="$(pub_kv BIG_MIN_KHZ "$_candidate")"; _pbmax="$(pub_kv BIG_MAX_KHZ "$_candidate")"
    _pgmin="$(pub_kv GPU_MIN_HZ "$_candidate")"; _pgmax="$(pub_kv GPU_MAX_HZ "$_candidate")"
    _plan_state=PROPOSED
    [ "$_cons_state" = PENDING_SHADOW ] && _plan_state=PENDING_SHADOW
    [ "$_shadow_state" = PASS ] && _plan_state=SHADOW_PASS
    [ "$_exec_state" = APPLIED ] && [ "$_readback" = VERIFIED ] && _plan_state=PROMOTED
    [ "$_exec_state" = ROLLED_BACK ] && _plan_state=ROLLED_BACK
    [ "$_exec_state" = ROLLBACK_FAILED ] && _plan_state=ROLLBACK_FAILED
    _plan_line="$_epoch,$_plan_state,$_pc,AI_CONSENSUS_MEASURED_ENVELOPE,ADAPTIVE,LEARNED,$_plmin,$_plmax,$_pbmin,$_pbmax,$_pgmin,$_pgmax"
  fi

  _publish_at=$(date +%s)
  _observer_pid="$(cat "$_root/runtime/locks/observer.lock/pid" 2>/dev/null | head -n1)"
  case "$_observer_pid" in ''|*[!0-9]*) _observer_pid=UNKNOWN;; esac

  _tmp="$_out.tmp.$PPID"
  {
    echo "__INSTALLED__"; echo 1
    echo "__VERSION__"; echo "1.1.7-adaptivefix"
    echo "__RUNTIME__"
    # Runtime freshness tracks publication time; telemetry sample time stays in __TEL__.
    # Using observer cycle-start EPOCH here made a newly published snapshot appear
    # artificially old and could cross the APK's 15s runtime TTL.
    echo "UPDATED_AT=$_publish_at"; echo "ACTIVE=$_active"; echo "GAME=$([ "$_workload" = GAME ] && echo "$_pkg" || echo NA)"; echo "WINDOW_MODE=$_window"
    echo "CONTROLLER_PID=$_observer_pid"; echo "PREDICTOR_PID="; echo "USER_MODE=$_exec_mode"
    echo "TOP_PACKAGE=$_top_pkg"; echo "PACKAGE_SOURCE=$_pkg_source"; echo "VISIBLE_GAME=$_visible_game"; echo "SNAPSHOT_GENERATION=$_generation"
    echo "SESSION_PACKAGE_SAMPLES=$_session_samples"; echo "LEARNING_SAMPLES=$_samples"; echo "LEARNING_CONFIDENCE=$_confidence"; echo "LEARNED_STATE=$_learning"
    echo "__TEL__"; echo "$_tel"
    echo "__BRAIN__"
    _brain="$_active_brain_source"
    [ "$_brain" = NONE ] && {
      case "$_gem" in CANDIDATE|OBSERVE|READY) _brain=GEMINI;; *) _brain=$([ "$_hmode" = TAKEOVER ] || [ "$_hmode" = TAKEOVER_CLOUD_ESCALATED ] && echo HERMES_H2 || echo OBSERVER);; esac
    }
    echo "CURRENT_BRAIN=$_brain"
    echo "PRIMARY_BRAIN=GEMINI"
    echo "DEPUTY_BRAIN=HERMES_H2"
    echo "THIRD_BRAIN=NONE"
    echo "ONE_HERMES=LOCAL_PLUS_CLOUD_ONE_IDENTITY"
    echo "HERMES_MODE=$_hmode"
    echo "HERMES_ACTIVE_SOURCE=$_hactive"
    echo "HERMES_CLOUD_USED=$_hcloud_used"
    echo "HERMES_CLOUD_ACTIVE=$_hcloud_active"
    echo "HERMES_CLOUD_LAST_SUCCESS_AGE_SEC=$_hcloud_last_age"
    echo "HERMES_CLOUD_LAST_ROUTE=$_hcloud_last_route"
    echo "HERMES_CLOUD_LAST_MODEL=$_hcloud_last_model"
    echo "HERMES_CLOUD_LAST_VERDICT=$_hcloud_last_verdict"
    echo "HERMES_CLOUD_POLICY=ON_DEMAND_NEURON_GUARDED"
    echo "OPTIMIZATION_OBJECTIVE=HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD"
    echo "FINAL_SOURCE=$([ "$_exec_state" = APPLIED ] && echo AI_AGENT_LOCAL_CONTROLLER || echo MEASURED_DEVICE)"
    echo "BRAIN_MODE=ADAPTIVE"
    echo "BRAIN_PROFILE=LEARNED"
    echo "FINAL_PROFILE=$([ "$_exec_state" = APPLIED ] && echo ADAPTIVE_LEARNED || echo LEARNED_PENDING)"
    echo "FINAL_ADJUSTMENT=$([ "$_exec_state" = APPLIED ] && echo ACTIVE || echo NONE)"
    echo "EXEC_MODE=$([ "$_exec_state" = APPLIED ] && echo ADAPTIVE_AUTO || echo GATED_AUTO)"
    _live_little="${_little_active_min}-${_little_active_max}"
    _live_big="${_big_active_min}-${_big_active_max}"
    _live_gpu="${_gpu_active_min}-${_gpu_active_max}"
    case "$_live_little" in *NA*|*-|"-"*) _live_little=$([ "$_exec_state" = APPLIED ] && echo "$_exec_little" || echo "$_lmin-$_lmax");; esac
    case "$_live_big" in *NA*|*-|"-"*) _live_big=$([ "$_exec_state" = APPLIED ] && echo "$_exec_big" || echo "$_bmin-$_bmax");; esac
    case "$_live_gpu" in *NA*|*-|"-"*) _live_gpu=$([ "$_exec_state" = APPLIED ] && echo "$_exec_gpu" || echo "$_gmin-$_gmax");; esac
    echo "EXEC_LITTLE=$_live_little"
    echo "EXEC_BIG=$_live_big"
    echo "EXEC_GPU=$_live_gpu"
    echo "EXEC_RANGE_SOURCE=LIVE_POLICY_BOUNDS"
    echo "CLOUD_CONNECTION_STATUS=$_cloud_connection"; echo "CLOUD_PROVIDER=MULTI"
    echo "GEMINI_CONNECTION_STATUS=$_gem_connection"; echo "GEMINI_HTTP_CODE=$_gem_http"; echo "GEMINI_KEY_COUNT=$_gem_count"; echo "GEMINI_READY_COUNT=$_gem_ready"; echo "GEMINI_COOLDOWN_COUNT=$_gem_cd"
    echo "GEMINI_REASONING_GUARD_SEC=$_gem_guard_sec"; echo "GEMINI_REASONING_GUARD_REASON=$_gem_guard_reason"; echo "GEMINI_LAST_SUCCESS_AGE_SEC=$_gem_last_success_age"
    echo "HERMES_CONNECTION_STATUS=$_hermes_connection"; echo "HERMES_CLOUD_CONNECTION_STATUS=$_hermes_cloud_connection"
    _cloud_control=NO; _cloud_controller=NONE
    case "$_active_brain_source" in GEMINI) _cloud_control=YES; _cloud_controller=GEMINI;; HERMES_CLOUD) _cloud_control=YES; _cloud_controller=HERMES_CLOUD;; esac
    echo "CLOUD_IN_CONTROL=$_cloud_control"; echo "CLOUD_CONTROL_PROVIDER=$_cloud_controller"; echo "CLOUD_PLAN_PROVIDER=$_plan_provider"
    echo "CLOUD_PLAN_INTENT=$_plan_intent"
    echo "CLOUD_PLAN_ACTUATORS=$_plan_actuators"
    echo "CLOUD_PLAN_STATE=$_cloud_plan_state"; echo "CLOUD_PLAN_SCORE=$_cloud_plan_score"; echo "CLOUD_PLAN_REASON=$(pub_clean "$_cloud_plan_reason")"
    echo "HERMES_PROPOSAL_STATE=$_hlocal"; echo "HERMES_PROPOSAL_CONFIDENCE=$_hconf"; echo "HERMES_PROFILE=ADAPTIVE_NO_FIXED_PROFILE"
    echo "HERMES_REASON=$(pub_clean "$_hreason")"; echo "HERMES_BACKEND=$([ "$_hroute" = LOCAL ] && echo LOCAL || echo CLOUD)"
    echo "HERMES_CLOUD_STATE=$_hcloud"; echo "HERMES_CLOUD_AUTH=$_hauth"
    echo "HERMES_CLOUD_ROUTE=$_hroute"; echo "HERMES_CLOUD_MODEL=$_hmodel"; echo "HERMES_CLOUD_HTTP_CODE=$_hhttp"
    echo "HERMES_CLOUD_REASON=$(pub_clean "$_hreason")"; echo "HERMES_NEURON_USED_EST=$_neuron_used"; echo "HERMES_NEURON_LIMIT=$_neuron_limit"; echo "HERMES_NEURON_TIER=$_neuron_tier"; echo "HERMES_NEURON_STATUS=LIVE_DAILY_USAGE"; echo "HERMES_NEURON_RESET=00:00_UTC_07:00_WIB"; echo "HERMES_NEURON_ACCOUNTING=SUCCESSFUL_HERMES_CLOUD_ONLY_NO_FORCED_QUOTA"
    echo "AGENT_VERSION=ADAPTIVE_V3"; echo "AGENT_ROLE=DEVICE_TRUTH_ORCHESTRATOR_AND_HARDWARE_CONTROLLER"; echo "AGENT_STATE=$_cons_state"
    echo "AGENT_INPUT_SOURCE=DEVICE_TRUTH"; echo "AGENT_DECISION_AUTHORITY=ACTIVE_BRAIN_BOUND_TO_EVIDENCE"; echo "AGENT_EXECUTION_OWNER=AI_AGENT"
    echo "AGENT_HARDWARE_AUTHORITY=FULL_LOCAL_GATED"; echo "AGENT_HARDWARE_TRUTH_SOURCE=AI_AGENT_SYSFS_READBACK"
    echo "AGENT_HARDWARE_TRUTH_AUTHORITY=MEASURED"; echo "AGENT_MUST_OBEY_ACTIVE_BRAIN=YES_WITH_SAFETY_GATES"
    echo "AGENT_CAN_CHOOSE_BRAIN=FAILOVER_CONTRACT_ONLY"; echo "AGENT_CAN_OVERRIDE_BRAIN=SAFETY_ONLY"; echo "AGENT_EXECUTION_BACKEND=INTERNAL_EXECUTOR_WORKER"
    echo "AGENT_LAST_VALIDATION=$_cons_state"; echo "AGENT_LAST_READBACK=$_readback"; echo "AGENT_ACTIVE_INTENT=$_exec_intent"; echo "AGENT_ACTIVE_ACTUATORS=$_exec_actuators"; echo "DECISION_PRIORITY=SAFETY_GATES>FRAME_STABILITY>THERMAL_COMFORT>MINIMUM_POWER"
    echo "THOUGHT_FRESH=$_thought_fresh"; echo "THOUGHT_AGE_SEC=$_thought_age"
    echo "__THOUGHTS__"; echo "SOURCE=$_thought_source"; echo "STATUS=$_thought_status"; echo "CONFIDENCE=$_thought_conf"; echo "TEXT=$(pub_clean_long "$_thought")"; echo "CONTEXT_PACKAGE=$_pkg"; echo "CONTEXT_CLASS=$_workload"; echo "REASON=$(pub_clean "$_thought_reason")"; echo "EVIDENCE=$(pub_clean "$_thought_evidence")"; echo "AT=$((_now-_thought_age))"
    echo "__MEMORY__"; echo "USED_BYTES=$_memory_used_bytes"; echo "MAX_BYTES=104857600"; echo "CAPACITY_KIND=PERSISTENT_STORAGE_NOT_RAM"; echo "LEDGER_ROWS=$_knowledge_rows"; echo "MODEL_SAMPLE_ROWS=$_samples"; echo "THOUGHT_KNOWLEDGE_ROWS=$_thought_knowledge_rows"; echo "REJECT_KNOWLEDGE_ROWS=$_reject_knowledge_rows"; echo "HARDWARE_OUTCOME_ROWS=$_outcome_rows"; echo "KEEP_ROWS=$_outcome_keep"; echo "ROLLBACK_ROWS=$_outcome_rollback"; echo "ROLLBACK_FAILED_ROWS=$_outcome_rollback_failed"; echo "RECENT_OUTCOME_ROWS=$_recent_outcome_rows"; echo "RECENT_KEEP_ROWS=$_recent_keep"; echo "RECENT_ROLLBACK_ROWS=$_recent_rollback"; echo "RECENT_ROLLBACK_FAILED_ROWS=$_recent_rollback_failed"; echo "VALIDATION_OUTCOME_ROWS=$_validation_outcome_rows"; echo "VALIDATION_KEEP_ROWS=$_validation_keep"; echo "VALIDATION_ROLLBACK_ROWS=$_validation_rollback"; echo "VALIDATION_ROLLBACK_FAILED_ROWS=$_validation_rollback_failed"; echo "VALIDATION_SUPERSEDED_DRIFT_ROWS=$_validation_superseded_drift"; echo "MATURITY_PACKAGE=$_maturity_pkg"; echo "MATURITY_MODEL_STATE=$_maturity_learning"; echo "MATURITY_MODEL_SAMPLES=$_maturity_samples"; echo "MATURITY_MODEL_CONFIDENCE=$_maturity_confidence"; echo "PERMANENT_READINESS=$_permanent_readiness"; echo "LAST_OUTCOME=$_outcome_last"; echo "LAST_OUTCOME_REASON=$(pub_clean "$_outcome_reason")"
    echo "__AUTHORITY__"; echo "STATE=AI_AGENT_LOCAL_GATED"; echo "HARDWARE_AUTHORITY=AI_AGENT"; echo "CLOUD_HARDWARE_AUTHORITY=NONE"; echo "SYSFS_WRITES=AI_AGENT_INTERNAL_EXECUTOR_ONLY"; echo "EXECUTOR=$_exec_state"
    echo "__SESSION_SAFETY__"; echo "STATE=FAIL_CLOSED"; echo "ROLLBACK=$_rollback"; echo "THERMAL_AUTHORITY=LOCAL_GUARD_PLUS_NATIVE"
    echo "__SUPERVISOR__"
    if [ "$_exec_age" -le 10 ] 2>/dev/null && [ "$_cons_age" -le 90 ] 2>/dev/null && [ "$_hermes_age" -le 180 ] 2>/dev/null && [ "$_gem_age" -le 180 ] 2>/dev/null; then echo "STATE=HEALTHY"; else echo "STATE=DEGRADED"; fi
    echo "PROCESS_MODEL=BOUNDED_OBSERVER_LOOPS"
    echo "GEMINI=$(pub_fresh "$_gem_state" UPDATED_AT 180)"
    echo "HERMES=$(pub_fresh "$_hermes_state" UPDATED_AT 180)"
    echo "CONSENSUS=$(pub_fresh "$_cons" UPDATED_AT 90)"
    echo "SHADOW=$(pub_fresh "$_shadow" UPDATED_AT 180)"
    echo "EXECUTOR=$(pub_fresh "$_execution" UPDATED_AT 10)"
    echo "RAILWAY=$(pub_fresh "$_railway" UPDATED_AT 90)"
    echo "__HERMES_CTX1_STATUS__"; echo "STATE=$_hlocal"; echo "MIGRATION=$_migration_state"
    echo "__HERMES_CTX1_RUNTIME__"; echo "PACKAGE=$_pkg"; echo "WORKLOAD=$_workload"; echo "WINDOW=$_window"
    echo "__HERMES_CTX1_SAFETY__"; echo "SYSFS=AI_AGENT_INTERNAL_EXECUTOR_ONLY"; echo "CONSENSUS=$_cons_state"; echo "SHADOW=$_shadow_state"; echo "EXECUTOR=$_exec_state"
    echo "__HERMES_CTX1_HARDWARE__"; echo "LITTLE=$_little"; echo "BIG=$_big"; echo "GPU=$_gpu"; echo "SKIN=$_skin_t"; echo "POWER=$_power"
    echo "__HERMES_CTX1_MEMORY__"; echo "SAMPLES=$_samples"; echo "BYTES=$_history_bytes"; echo "CREDENTIAL_FILES=$_credential_count"; echo "GEMINI_KEY_COUNT=$(pub_kv GEMINI_KEY_COUNT "$_migration")"; echo "HERMES_ACCESS_KEY_PRESENT=$(pub_kv HERMES_ACCESS_KEY_PRESENT "$_migration")"; echo "NEURON_LOCAL_ESTIMATE_PRESENT=$(pub_kv NEURON_LOCAL_ESTIMATE_PRESENT "$_migration")"
    echo "__HERMES_CTX1_LEARNING__"; echo "STATE=$_learning"; echo "CONFIDENCE=$_confidence"; echo "FRAME_EVIDENCE=$_frame_evidence"
    echo "__HERMES_COGNITION_STATUS__"; echo "STATE=$_hlocal"; echo "MODE=OBSERVER_VNEXT"
    echo "__HERMES_MEMORY_VNEXT__"; echo "STATE=$_learning"; echo "SAMPLES=$_samples"; echo "SOURCE=STOCK_HISTORY"
    echo "__HERMES_REASONING_V2__"; echo "STATE=$_cons_state"; echo "CONTRACT=STRUCTURED_ENVELOPE_ONLY"
    echo "__HERMES_SKILLS_VNEXT__"; echo "STATE=$([ "$_hermes_age" -le 180 ] 2>/dev/null && echo AVAILABLE || echo STALE)"; echo "SKILLS=VALIDATE_OPP,THERMAL_GUARD,FRAME_GUARD,POWER_GUARD"
    echo "__HERMES_LEARNING_V2__"; echo "STATE=$_learning"; echo "PACKAGE=$_pkg"; echo "SAMPLES=$_samples"
    echo "__HERMES_RESEARCH_V2__"; echo "STATE=$_shadow_state"; echo "SHADOW_WINDOWS=$_shadow_n"
    echo "__HERMES_HUMAN_COMFORT__"; echo "COMFORT_MODEL=FRAME_STABILITY_PLUS_THERMAL_COMFORT"; echo "HEAT_SENSITIVITY=HIGH_USER_PREFERENCE"; echo "SOFT_SKIN_PRESSURE_C=42"; echo "COMFORT_PRESSURE=$_comfort_pressure"; echo "STATE=ACTIVE_REASONING_CONSTRAINT"; echo "DIRECT_CLOCK_EFFECT=GATED_BY_SHADOW_AND_EXECUTOR"; echo "FIXED_PRESET=DISABLED"
    echo "__HERMES_LANGUAGE__"; echo "STATE=STRUCTURED_ONLY"
    echo "__HERMES_MATH__"; echo "STATE=$_learning"; echo "VERIFY=$_shadow_state"; echo "INPUT_SANITY=MEASURED"; echo "TARGET_FRAME_MS=UNSPECIFIED_DEVICE_LEARNED"
    echo "__HERMES_KERNEL1__"; echo "STATE=GATED"; echo "STRATEGY=MEASURED_ADAPTIVE"; echo "BOTTLENECK=$_exec_reason"; echo "CAPABILITIES_TOTAL=$_cap_count"; echo "ACTUATORS_TOTAL=$_actuator_truth"; echo "ACTION_COUNT=$_action_count"; echo "ROOT_AUTHORITY_OWNER=LOCAL_EXECUTOR"; echo "SYSFS_OWNER=LOCAL_EXECUTOR"
    echo "__AGENT_SYSFS1_CAPABILITY__"; echo "TOTAL=$_cap_count"; echo "ACTUATORS=$_actuator_truth"
    echo "__AGENT_SYSFS1_EXECUTION__"; echo "STATUS=$_exec_state"; echo "ACTION_COUNT=$_action_count"; echo "APPLIED_COUNT=$_action_count"; echo "FAILURE=$([ "$_exec_state" = ROLLED_BACK ] && echo "$_exec_reason" || echo NONE)"
    echo "__CONTROL_CENTER_SYNC__"
    echo "CONTRACT=DJAEGER_AI_ADAPTIVE_V3"; echo "MODULE_VERSION_CODE=$_module_code"; echo "EXPECTED_CONTROL_CENTER_VERSION_CODE=111"; echo "CONTROL_CENTER_VERSION_CODE=${_apk_ver:-UNVERIFIED}"
    echo "PAIR_VERIFIED=$_pair"; echo "HANDSHAKE_SCHEMA=${_hand_schema:-UNVERIFIED}"; echo "HANDSHAKE_ACK_ID=${_ack_id:-NONE}"; echo "HANDSHAKE_AGE_SEC=$_hand_age"
    echo "SNAPSHOT_GENERATION=$_generation"; echo "SNAPSHOT_FRESH=YES"
    echo "SHARED_INTELLIGENCE=GEMINI_PRIMARY_PLUS_ONE_HERMES_DEPUTY"; echo "GEMINI_INTELLIGENCE_SCOPE=PRIMARY_HIGHEST_FULL_REASONING_STRATEGY"; echo "HERMES_INTELLIGENCE_SCOPE=ONE_HERMES_FULL_DEPUTY_LOCAL_PLUS_CLOUD"
    echo "GEMINI_REASONING_LIMIT=NO_DIRECT_SYSFS"; echo "HERMES_TEACHER_LOOP=CONTINUITY_MEMORY_OUTCOME_FEEDBACK"; echo "HERMES_CLOUD_POLICY=ON_DEMAND_NEURON_GUARDED"; echo "OPTIMIZATION_OBJECTIVE=HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD"
    echo "GEMINI_CONNECTION=$_gem_connection"; echo "HERMES_CONNECTION=$_hermes_connection"
    echo "GEMINI_KEY_COUNT=$_gem_count"; echo "GEMINI_READY_COUNT=$_gem_ready"; echo "GEMINI_COOLDOWN_COUNT=$_gem_cd"; echo "HERMES_AUTH=$_hauth"
    echo "HERMES_CLOUD=ONE_HERMES_CLOUD_COGNITION"; echo "HERMES_CLOUD_ROLE=STRONGEST_HERMES_CLOUD_BRAIN_ON_DEMAND"; echo "HERMES_BACKEND_PRIORITY=LOCAL_CONTINUITY_THEN_CLOUD_ESCALATION_WHEN_NEEDED"; echo "WORKLOAD_FINAL=ADAPTIVE_CLASSIFIER_V2"; echo "DUAL_REGISTRY=SEPARATE"; echo "PREEXEC_WORKLOAD_GUARD=ACTIVE_LOCAL_GATED"
    echo "__STRATEGY_RESULT__"; echo "VALIDATION=$_cons_state"; echo "INTENT=$_plan_intent"; echo "ACTUATORS=$_plan_actuators"; echo "READBACK=$_readback"; echo "OUTCOME=$_outcome_last"; echo "OUTCOME_REASON=$(pub_clean "$_outcome_reason")"; echo "SHADOW=$_shadow_state"
    echo "__ENV__"; [ -r "$_learn" ] && cat "$_learn"
    echo "__HTTP__"; [ -r "$_gem_state" ] && cat "$_gem_state" || true
    echo "__SERVER__"; [ -r "$_hermes_state" ] && cat "$_hermes_state" || true
    echo "__DECISIONS__"
    echo "__PLANS__"; [ -n "$_plan_line" ] && echo "$_plan_line"
    echo "__FRAME__"; echo "$_frame_line"
    echo "__LOG__"; [ -r "$_root/runtime/events.log" ] && tail -n 80 "$_root/runtime/events.log" || true
    echo "__NETWORK__"; if [ -r "$_network" ]; then cat "$_network"; else echo "SESSION_ACTIVE=0"; echo "QUALITY=UNAVAILABLE"; echo "SOURCE=NETWORK_OBSERVER_MISSING"; echo "UPDATED_AT=$_now"; fi
    echo "__REASONING__"; echo "STATE=$_cons_state"
    echo "__RESYNC__"; echo "STATE=$([ "$_pair" = YES ] && echo VERIFIED || echo UNVERIFIED)"; echo "CONTRACT=DJAEGER_AI_ADAPTIVE_V3"; echo "ACK_ID=${_ack_id:-NONE}"; echo "GENERATION=$_generation"
    echo "__EXECUTION__"; echo "STATUS=$_exec_state"; echo "READBACK=$_readback"; echo "ROLLBACK=$_rollback"; echo "RAILWAY=$_railway_state"
    echo "__POLICY_CONTEXT__"; echo "PACKAGE=$_pkg"; echo "WORKLOAD=$_workload"; echo "BASELINE=$_learning"
    echo "__ATTRIBUTION__"; echo "SOURCE=MEASURED_STOCK"
    echo "__WORKLOAD_CONTEXT__"; echo "PACKAGE=$_pkg"; echo "TOP_PACKAGE=$_top_pkg"; echo "VISIBLE_GAME=$_visible_game"; echo "PACKAGE_SOURCE=$_pkg_source"; echo "WORKLOAD_CLASS=$_workload"; echo "WORKLOAD_PROFILE=$_runtime_profile"; echo "SUBJECT_CLASS=$_workload"; echo "REASONING_DOMAIN=$_workload"; echo "GAME_SEMANTICS=REGISTRY_PLUS_VISIBLE_WINDOW"; echo "FRAME_SEMANTICS=EVIDENCE_ONLY"; echo "SOURCE=$_workload_source"; echo "CONFIDENCE=$([ "$_workload" = GAME ] && echo 100 || echo 70)"; echo "GAME_REGISTRY_AUTHORITY=MANUAL_PLUS_BUILTIN"
    echo "__WORKLOAD_GATE__"; echo "GAME_ONLY=ADAPTIVE_GATED"; echo "APP_ONLY=OBSERVE"; echo "SYSTEM_ONLY=OBSERVE"
    echo "__PROPOSAL_BINDING__"; echo "LATEST_PROPOSAL_SOURCE=$_plan_provider"; echo "LATEST_SUBJECT_PACKAGE=$_pkg"; echo "LATEST_SUBJECT_CLASS=$_workload"; echo "LATEST_BINDING_DECISION=$_cons_state"; echo "LATEST_BINDING_REASON=$_exec_reason"
    echo "__WORKLOAD_FINAL__"; echo "STATUS=ACTIVE"; echo "DUAL_REGISTRY=SEPARATE"; echo "REGISTRY_CONFLICTS=0"; echo "EXECUTION_SCOPE=GAME_ONLY_LOCAL_GATED"; echo "APP_GAME_POLICY=NEVER_PROMOTE"; echo "SYSTEM_GAME_POLICY=NEVER_PROMOTE"; echo "UNKNOWN_GAME_POLICY=OBSERVE_ONLY"; echo "STALE_POLICY=FAIL_CLOSED"; echo "LEARNING_ISOLATION=PER_PACKAGE"; echo "ROOT_AUTHORITY_CHANGED=LOCAL_EXECUTOR_ONLY"; echo "SYSFS_AUTHORITY_CHANGED=LOCAL_EXECUTOR_ONLY"; echo "RESCUE_PATH_CHANGED=NO"
    echo "__WORKLOAD_EXEC_GUARD__"; echo "DECISION=$([ "$_exec_state" = APPLIED ] && echo ALLOW || echo BLOCK)"; echo "REASON=$_exec_reason"
    echo "__APP_REGISTRY__"; [ -r "$_root/config/app_registry.tsv" ] && cat "$_root/config/app_registry.tsv" || true
    echo "__GAME_REGISTRY_MANUAL__"; [ -r "$_root/config/game_registry.tsv" ] && cat "$_root/config/game_registry.tsv" || true
    echo "__BUG_HEALTH__"; echo "HEALTH=$_bug_health"; echo "STATE=$_bug_health"; echo "OPEN_BUG=$_bug_open"; echo "SEVERITY=$_bug_severity"; echo "COMPONENT=$_bug_component"; echo "CODE=$_bug_code"; echo "SUMMARY=$(pub_clean "$_bug_summary")"; echo "FACTS=$(pub_clean "$_bug_facts")"; echo "ACTION=$(pub_clean "$_bug_action")"; echo "RECOVERY=$_bug_recovery"; echo "UPDATED_AT=$_epoch"
    echo "__BUG_EVENTS__"; [ "$_bug_code" != NONE ] && echo "$_epoch|$_bug_severity|$_bug_component|$_bug_code|$(pub_clean "$_bug_summary")" || true
  } > "$_tmp"
  chmod 644 "$_tmp" 2>/dev/null
  mv -f "$_tmp" "$_out"
  [ "$_frame_src" = "$_frame" ] || rm -f "$_frame_src" 2>/dev/null
}
