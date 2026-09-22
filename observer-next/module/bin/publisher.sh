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
  printf '%s' "$1" | tr '\r\n\t' '   ' | tr -cd 'A-Za-z0-9._:+/%=,@ -' | cut -c1-420
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
  _shadow="$_root/runtime/shadow.env"
  _execution="$_root/runtime/execution.env"
  _outcomes="$_root/history/outcomes.csv"
  _railway="$_root/runtime/railway.env"
  _recovery="$_root/runtime/credential_recovery.env"
  _neuron="$_root/config/hermes_neuron_legacy.env"
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
  _samples="$(pub_kv PACKAGE_SAMPLES "$_snap")"; case "$_samples" in ''|*[!0-9]*) _samples=0;; esac
  _learn_pkg="$(pub_kv PACKAGE "$_learn")"
  if [ -n "$_learn_pkg" ] && [ "$_learn_pkg" = "$_pkg" ]; then
    _learning="$(pub_kv STATE "$_learn")"
    _confidence="$(pub_kv CONFIDENCE "$_learn")"; case "$_confidence" in ''|*[!0-9]*) _confidence=0;; esac
  else
    _learning="$(pub_kv LEARNING_STATE "$_snap")"
    _confidence=0
  fi
  [ -n "$_learning" ] || _learning=WAITING

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
  _gem_conf="$(pub_kv CONFIDENCE "$_gem_prop")"; case "$_gem_conf" in ''|*[!0-9]*) _gem_conf=0;; esac
  _gem_reason="$(pub_kv REASON "$_gem_prop")"; [ -n "$_gem_reason" ] || _gem_reason="$(pub_kv GEMINI_DETAIL "$_gem_state")"
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
  _hconf="$(pub_kv CONFIDENCE "$_local_vote")"; case "$_hconf" in ''|*[!0-9]*) _hconf=0;; esac
  _cons_state="$(pub_kv CONSENSUS_STATE "$_cons")"; [ -n "$_cons_state" ] || _cons_state=OBSERVING
  _active_brain_source="$(pub_kv ACTIVE_BRAIN_SOURCE "$_cons")"; [ -n "$_active_brain_source" ] || _active_brain_source=NONE
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
  _neuron_used="$(pub_kv USED_EST "$_neuron")"; _neuron_limit="$(pub_kv LIMIT "$_neuron")"
  case "$_neuron_used:$_neuron_limit" in
    *[!0-9:]*|:*) _neuron_used=UNAVAILABLE; _neuron_limit=UNAVAILABLE; _neuron_tier=UNREPORTED ;;
    *) _neuron_tier=LOCAL_DEVICE_ESTIMATE ;;
  esac

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
  _hermes_connection=WAITING
  case "$_hcloud" in
    ONLINE|APPROVED|REJECTED) _hermes_connection=ONLINE ;;
    REACHABLE_IDLE) _hermes_connection=REACHABLE ;;
    NO_KEY) _hermes_connection=NOT_CONFIGURED ;;
    AUTH_ERROR) _hermes_connection=AUTH_ERROR ;;
    HTTP_ERROR|UNAVAILABLE|OFFLINE) _hermes_connection=OFFLINE ;;
    *) [ "$_hauth" = NOT_CONFIGURED ] && _hermes_connection=NOT_CONFIGURED ;;
  esac
  [ "$_hermes_age" -le 180 ] 2>/dev/null || _hermes_connection=STALE

  _module_code=$(sed -n 's/^versionCode=//p' "${MODDIR:-/data/adb/modules/djaeger_ai_observer}/module.prop" 2>/dev/null | head -n1)
  case "$_module_code" in ''|*[!0-9]*) _module_code=0;; esac
  _apk_ver="$(pub_kv APK_VERSION_CODE "$_handshake")"
  _expected_apk="$(pub_kv EXPECTED_APK_VERSION_CODE "$_handshake")"; [ -n "$_expected_apk" ] || _expected_apk=107
  _hand_schema="$(pub_kv SCHEMA "$_handshake")"
  _ack_id="$(pub_kv ACK_ID "$_handshake")"
  _ack_at="$(pub_kv ACK_AT "$_handshake")"; case "$_ack_at" in ''|*[!0-9]*) _ack_at=0;; esac
  _hand_age=$((_now-_ack_at)); [ "$_hand_age" -ge 0 ] 2>/dev/null || _hand_age=999999
  _pair="$(pub_kv PAIR_VERIFIED "$_handshake")"
  [ "$_pair" = YES ] && [ "$_hand_schema" = DJAEGER_AI_ADAPTIVE_V2 ] && [ "$_hand_age" -le 86400 ] 2>/dev/null || _pair=NO
  _generation=$(cat "$_genfile" 2>/dev/null | head -n1); case "$_generation" in ''|*[!0-9]*) _generation=0;; esac
  _generation=$((_generation+1))
  _gen_tmp="$(mktemp "${_genfile}.tmp.XXXXXX" 2>/dev/null)"
  [ -n "$_gen_tmp" ] || _gen_tmp="${_genfile}.tmp.${_now}.${_generation}"
  printf '%s\n' "$_generation" > "$_gen_tmp"; chmod 600 "$_gen_tmp" 2>/dev/null; mv -f "$_gen_tmp" "$_genfile"

  _cloud_connection="GEMINI_$_gem_connection|HERMES_$_hermes_connection"

  # Brain plan truth. Gemini is primary; ONE HERMES is deputy takeover.
  _plan_provider=NONE
  _cloud_plan_state=NOT_USED
  _cloud_plan_score=0
  _cloud_plan_reason=NO_ACTIVE_BRAIN_PLAN
  if [ -r "$_candidate" ] && [ "$(pub_kv PACKAGE "$_candidate")" = "$_pkg" ]; then
    _plan_provider="$(pub_kv BRAIN_SOURCE "$_candidate")"; [ -n "$_plan_provider" ] || _plan_provider=UNKNOWN
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

  # Dynamic THOUGHT follows the actual brain hierarchy and Agent outcome.
  _thought_source=OBSERVER_LOCAL
  _thought_status=OBSERVING
  _thought_age=$((_now-_epoch)); [ "$_thought_age" -ge 0 ] 2>/dev/null || _thought_age=999999
  _thought_conf="$_confidence"
  _thought_reason=MEASURED_DEVICE
  _thought_evidence="telemetry=$_seq frame=$_frame_evidence learning=$_learning samples=$_samples"
  _thought="AI Agent mengumpulkan Device Truth untuk $_pkg. Tujuan tetap: kestabilan frame terlebih dahulu, lalu daya serendah mungkin tanpa mengorbankan kestabilan."

  case "$_active_brain_source" in
    GEMINI)
      _thought_source=GEMINI
      _thought_status=PRIMARY
      _thought_conf="$_gem_conf"
      _thought_reason="$_gem_reason"
      _thought_evidence="brain=GEMINI role=PRIMARY frame=$_frame_evidence"
      _thought="Gemini adalah otak utama dan sedang memimpin reasoning untuk $_pkg. Hasilnya diteruskan ke ONE HERMES sebagai deputy continuity sebelum AI Agent melakukan shadow, safety, dan kontrol hardware."
      ;;
    HERMES_LOCAL)
      _thought_source=HERMES_H2
      _thought_status=DEPUTY_LOCAL_TAKEOVER
      _thought_conf="$_hconf"
      _thought_reason="$_hreason"
      _thought_evidence="brain=ONE_HERMES source=LOCAL gemini=$_gem"
      _thought="Gemini tidak tersedia. ONE HERMES mengambil alih melalui Hermes Local menggunakan memory dan strategi proven tanpa memakai neuron Cloud."
      ;;
    HERMES_CLOUD)
      _thought_source=HERMES_H2
      _thought_status=DEPUTY_CLOUD_TAKEOVER
      _thought_conf="$_cloud_plan_score"
      _thought_reason="$_hreason"
      _thought_evidence="brain=ONE_HERMES source=CLOUD route=$_hroute model=$_hmodel cloud_used=$_hcloud_used"
      _thought="Gemini tidak tersedia dan Hermes Local tidak memiliki strategi proven yang cukup. ONE HERMES menyalakan Hermes Cloud secara selektif untuk reasoning takeover; penggunaan Cloud tetap neuron-guarded."
      ;;
    HERMES_H2)
      _thought_source=HERMES_H2
      _thought_status=DEPUTY_OBSERVE
      _thought_reason="$_hreason"
      _thought_evidence="brain=ONE_HERMES mode=$_hmode"
      _thought="Gemini tidak tersedia. ONE HERMES aktif sebagai deputy tetapi memilih tidak mengubah hardware karena evidence belum membutuhkan perubahan."
      ;;
  esac

  if [ "$_cons_state" = PENDING_SHADOW ]; then
    _thought_status=PENDING_SHADOW
    _thought="Strategi dari $_active_brain_source sedang diuji shadow. Frame stability adalah syarat pertama; daya minimum dinilai setelah kestabilan frame terpenuhi."
  fi
  if [ "$_shadow_state" = PASS ]; then
    _thought_status=SHADOW_PASS
    _thought="Shadow lulus kontrak frame-first/minimum-power. AI Agent boleh menjalankan transaksi hardware lokal yang terikat digest dan tetap wajib exact readback."
  fi
  if [ "$_exec_state" = APPLIED ] && [ "$_readback" = VERIFIED ]; then
    _thought_source=AI_AGENT
    _thought_status=APPLIED_VERIFIED
    _thought_age="$_exec_age"
    _thought_reason="$_exec_reason"
    _thought_evidence="little=$_exec_little big=$_exec_big gpu=$_exec_gpu readback=$_readback"
    _thought="AI Agent menerapkan strategi $_active_brain_source dan readback VERIFIED: Little $_exec_little, Big $_exec_big, GPU $_exec_gpu. Outcome frame dan daya terus dipantau untuk KEEP atau ROLLBACK."
  elif [ "$_exec_state" = ROLLED_BACK ]; then
    _thought_source=AI_AGENT
    _thought_status=ROLLED_BACK
    _thought_age="$_exec_age"
    _thought_reason="$_exec_reason"
    _thought_evidence="rollback=$_rollback readback=$_readback"
    _thought="AI Agent membatalkan strategi karena $_exec_reason dan mengembalikan hardware ke state sebelumnya."
  elif [ "$_exec_state" = ROLLBACK_FAILED ]; then
    _thought_source=AI_AGENT
    _thought_status=ROLLBACK_FAILED
    _thought_age="$_exec_age"
    _thought_conf=0
    _thought_reason="$_exec_reason"
    _thought_evidence="rollback=$_rollback readback=$_readback"
    _thought="AI Agent fail-closed karena recovery SYSFS belum terverifikasi."
  fi
  _thought_fresh=0; [ "$_thought_age" -le 180 ] 2>/dev/null && _thought_fresh=1

  if [ -r "$_root/history/telemetry.csv" ]; then _history_bytes="$(wc -c < "$_root/history/telemetry.csv" 2>/dev/null)"
  else _history_bytes=0
  fi
  case "$_history_bytes" in ''|*[!0-9]*) _history_bytes=0;; esac
  _outcome_rows=0; _outcome_keep=0; _outcome_rollback=0; _outcome_last=NONE; _outcome_reason=NONE
  if [ -r "$_outcomes" ]; then
    _outcome_rows="$(awk -F, 'NR>1{n++}END{print n+0}' "$_outcomes" 2>/dev/null)"
    _outcome_keep="$(awk -F, 'NR>1&&($4=="KEPT"||$4=="APPLIED_VERIFIED"){n++}END{print n+0}' "$_outcomes" 2>/dev/null)"
    _outcome_rollback="$(awk -F, 'NR>1&&($4=="ROLLED_BACK"||$4=="ROLLBACK_FAILED"){n++}END{print n+0}' "$_outcomes" 2>/dev/null)"
    _outcome_last="$(awk -F, 'NR>1{v=$4}END{print v}' "$_outcomes" 2>/dev/null)"; [ -n "$_outcome_last" ] || _outcome_last=NONE
    _outcome_reason="$(awk -F, 'NR>1{v=$5}END{print v}' "$_outcomes" 2>/dev/null)"; [ -n "$_outcome_reason" ] || _outcome_reason=NONE
  fi
  case "$_outcome_rows" in ''|*[!0-9]*) _outcome_rows=0;; esac
  case "$_outcome_keep" in ''|*[!0-9]*) _outcome_keep=0;; esac
  case "$_outcome_rollback" in ''|*[!0-9]*) _outcome_rollback=0;; esac
  _exec_mode="$(cat "$_root/config/execution_mode" 2>/dev/null | head -n1)"; [ -n "$_exec_mode" ] || _exec_mode=AUTO
  _runtime_profile=LEARNED_PENDING; [ "$_exec_state" = APPLIED ] && _runtime_profile=ADAPTIVE_LEARNED
  _tel="$_epoch,$_cpu_t,$_gpu_t,$_skin_t,$_bat_t,$_little,$_big,$_gpu,$_runtime_profile,$_frame_ms,$_fps,$_jank,$_p95,$_p99,0,$_battery_status,$_current,$_voltage,$_power,$_power_valid,$_power_reason,$_pkg,$_window"
  _frame_line="$_epoch,$_runtime_profile,$_frame_ms,$_fps,$_jank,$_p95,$_p99"
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

  _tmp="$_out.tmp.$$"
  {
    echo "__INSTALLED__"; echo 1
    echo "__VERSION__"; echo "1.1.3-runtimefix"
    echo "__RUNTIME__"
    echo "UPDATED_AT=$_epoch"; echo "ACTIVE=$_active"; echo "GAME=$([ "$_workload" = GAME ] && echo "$_pkg" || echo NA)"; echo "WINDOW_MODE=$_window"
    echo "CONTROLLER_PID=${OBSERVER_PID:-UNKNOWN}"; echo "PREDICTOR_PID="; echo "USER_MODE=$_exec_mode"
    echo "TOP_PACKAGE=$_top_pkg"; echo "PACKAGE_SOURCE=$_pkg_source"; echo "VISIBLE_GAME=$_visible_game"; echo "SNAPSHOT_GENERATION=$_generation"
    echo "LEARNING_SAMPLES=$_samples"; echo "LEARNING_CONFIDENCE=$_confidence"; echo "LEARNED_STATE=$_learning"
    echo "__TEL__"; echo "$_tel"
    echo "__BRAIN__"
    _brain="$_active_brain_source"
    [ "$_brain" = NONE ] && {
      case "$_gem" in CANDIDATE|OBSERVE|READY) _brain=GEMINI;; *) _brain=$([ "$_hmode" = TAKEOVER ] || [ "$_hmode" = TAKEOVER_CLOUD_ESCALATED ] && echo HERMES_H2 || echo OBSERVER);; esac
    }
    echo "CURRENT_BRAIN=$_brain"
    echo "PRIMARY_BRAIN=GEMINI"
    echo "DEPUTY_BRAIN=HERMES_H2"
    echo "ONE_HERMES=LOCAL_PLUS_CLOUD_ONE_IDENTITY"
    echo "HERMES_MODE=$_hmode"
    echo "HERMES_ACTIVE_SOURCE=$_hactive"
    echo "HERMES_CLOUD_USED=$_hcloud_used"
    echo "HERMES_CLOUD_POLICY=ON_DEMAND_NEURON_GUARDED"
    echo "OPTIMIZATION_OBJECTIVE=FRAME_STABILITY_FIRST_MINIMUM_POWER_SECOND"
    echo "FINAL_SOURCE=$([ "$_exec_state" = APPLIED ] && echo AI_AGENT_LOCAL_CONTROLLER || echo MEASURED_DEVICE)"
    echo "BRAIN_MODE=ADAPTIVE"
    echo "BRAIN_PROFILE=LEARNED"
    echo "FINAL_PROFILE=$([ "$_exec_state" = APPLIED ] && echo ADAPTIVE_LEARNED || echo LEARNED_PENDING)"
    echo "FINAL_ADJUSTMENT=$([ "$_exec_state" = APPLIED ] && echo ACTIVE || echo NONE)"
    echo "EXEC_MODE=$([ "$_exec_state" = APPLIED ] && echo ADAPTIVE_AUTO || echo GATED_AUTO)"
    echo "EXEC_LITTLE=$([ "$_exec_state" = APPLIED ] && echo "$_exec_little" || echo "$_lmin-$_lmax")"
    echo "EXEC_BIG=$([ "$_exec_state" = APPLIED ] && echo "$_exec_big" || echo "$_bmin-$_bmax")"
    echo "EXEC_GPU=$([ "$_exec_state" = APPLIED ] && echo "$_exec_gpu" || echo "$_gmin-$_gmax")"
    echo "CLOUD_CONNECTION_STATUS=$_cloud_connection"; echo "CLOUD_PROVIDER=MULTI"
    echo "GEMINI_CONNECTION_STATUS=$_gem_connection"; echo "GEMINI_HTTP_CODE=$_gem_http"; echo "GEMINI_KEY_COUNT=$_gem_count"; echo "GEMINI_READY_COUNT=$_gem_ready"; echo "GEMINI_COOLDOWN_COUNT=$_gem_cd"
    echo "HERMES_CONNECTION_STATUS=$_hermes_connection"
    echo "CLOUD_IN_CONTROL=NO"; echo "CLOUD_CONTROL_PROVIDER=NONE"; echo "CLOUD_PLAN_PROVIDER=$_plan_provider"
    echo "CLOUD_PLAN_STATE=$_cloud_plan_state"; echo "CLOUD_PLAN_SCORE=$_cloud_plan_score"; echo "CLOUD_PLAN_REASON=$(pub_clean "$_cloud_plan_reason")"
    echo "HERMES_PROPOSAL_STATE=$_hlocal"; echo "HERMES_PROPOSAL_CONFIDENCE=$_hconf"; echo "HERMES_PROFILE=ADAPTIVE_NO_FIXED_PROFILE"
    echo "HERMES_REASON=$(pub_clean "$_hreason")"; echo "HERMES_BACKEND=$([ "$_hroute" = LOCAL ] && echo LOCAL || echo CLOUD)"
    echo "HERMES_CLOUD_STATE=$_hcloud"; echo "HERMES_CLOUD_AUTH=$_hauth"
    echo "HERMES_CLOUD_ROUTE=$_hroute"; echo "HERMES_CLOUD_MODEL=$_hmodel"; echo "HERMES_CLOUD_HTTP_CODE=$_hhttp"
    echo "HERMES_CLOUD_REASON=$(pub_clean "$_hreason")"; echo "HERMES_NEURON_USED_EST=$_neuron_used"; echo "HERMES_NEURON_LIMIT=$_neuron_limit"; echo "HERMES_NEURON_TIER=$_neuron_tier"; echo "HERMES_NEURON_ACCOUNTING=DEVICE_ESTIMATE_SEPARATE_FROM_PROVIDER_QUOTA"
    echo "AGENT_VERSION=ADAPTIVE_V3"; echo "AGENT_ROLE=DEVICE_TRUTH_ORCHESTRATOR_AND_HARDWARE_CONTROLLER"; echo "AGENT_STATE=$_cons_state"
    echo "AGENT_INPUT_SOURCE=DEVICE_TRUTH"; echo "AGENT_DECISION_AUTHORITY=ACTIVE_BRAIN_BOUND_TO_EVIDENCE"; echo "AGENT_EXECUTION_OWNER=AI_AGENT"
    echo "AGENT_HARDWARE_AUTHORITY=FULL_LOCAL_GATED"; echo "AGENT_HARDWARE_TRUTH_SOURCE=AI_AGENT_SYSFS_READBACK"
    echo "AGENT_HARDWARE_TRUTH_AUTHORITY=MEASURED"; echo "AGENT_MUST_OBEY_ACTIVE_BRAIN=YES_WITH_SAFETY_GATES"
    echo "AGENT_CAN_CHOOSE_BRAIN=FAILOVER_CONTRACT_ONLY"; echo "AGENT_CAN_OVERRIDE_BRAIN=SAFETY_ONLY"; echo "AGENT_EXECUTION_BACKEND=INTERNAL_EXECUTOR_WORKER"
    echo "AGENT_LAST_VALIDATION=$_cons_state"; echo "AGENT_LAST_READBACK=$_readback"; echo "DECISION_PRIORITY=FRAME_STABILITY>MINIMUM_POWER>SAFETY_GATES"
    echo "THOUGHT_FRESH=$_thought_fresh"; echo "THOUGHT_AGE_SEC=$_thought_age"
    echo "__THOUGHTS__"; echo "SOURCE=$_thought_source"; echo "STATUS=$_thought_status"; echo "CONFIDENCE=$_thought_conf"; echo "TEXT=$(pub_clean_long "$_thought")"; echo "CONTEXT_PACKAGE=$_pkg"; echo "CONTEXT_CLASS=$_workload"; echo "REASON=$(pub_clean "$_thought_reason")"; echo "EVIDENCE=$(pub_clean "$_thought_evidence")"; echo "AT=$((_now-_thought_age))"
    echo "__MEMORY__"; echo "USED_BYTES=$_history_bytes"; echo "MAX_BYTES=3145728"; echo "LEDGER_ROWS=$_samples"; echo "HARDWARE_OUTCOME_ROWS=$_outcome_rows"; echo "KEEP_ROWS=$_outcome_keep"; echo "ROLLBACK_ROWS=$_outcome_rollback"; echo "LAST_OUTCOME=$_outcome_last"; echo "LAST_OUTCOME_REASON=$(pub_clean "$_outcome_reason")"
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
    echo "__HERMES_HUMAN_COMFORT__"; echo "COMFORT_PRESET=LEARNED"; echo "STATE=FEEDBACK_RECORDED_AS_EVIDENCE"; echo "DIRECT_CLOCK_EFFECT=NONE"; echo "FIXED_PRESET=DISABLED"
    echo "__HERMES_LANGUAGE__"; echo "STATE=STRUCTURED_ONLY"
    echo "__HERMES_MATH__"; echo "STATE=$_learning"; echo "VERIFY=$_shadow_state"; echo "INPUT_SANITY=MEASURED"; echo "TARGET_FRAME_MS=UNSPECIFIED_DEVICE_LEARNED"
    echo "__HERMES_KERNEL1__"; echo "STATE=GATED"; echo "STRATEGY=MEASURED_ADAPTIVE"; echo "BOTTLENECK=$_exec_reason"; echo "CAPABILITIES_TOTAL=$_cap_count"; echo "ACTUATORS_TOTAL=$_actuator_truth"; echo "ACTION_COUNT=$_action_count"; echo "ROOT_AUTHORITY_OWNER=LOCAL_EXECUTOR"; echo "SYSFS_OWNER=LOCAL_EXECUTOR"
    echo "__AGENT_SYSFS1_CAPABILITY__"; echo "TOTAL=$_cap_count"; echo "ACTUATORS=$_actuator_truth"
    echo "__AGENT_SYSFS1_EXECUTION__"; echo "STATUS=$_exec_state"; echo "ACTION_COUNT=$_action_count"; echo "APPLIED_COUNT=$_action_count"; echo "FAILURE=$([ "$_exec_state" = ROLLED_BACK ] && echo "$_exec_reason" || echo NONE)"
    echo "__CONTROL_CENTER_SYNC__"
    echo "CONTRACT=DJAEGER_AI_ADAPTIVE_V2"; echo "MODULE_VERSION_CODE=$_module_code"; echo "EXPECTED_CONTROL_CENTER_VERSION_CODE=107"; echo "CONTROL_CENTER_VERSION_CODE=${_apk_ver:-UNVERIFIED}"
    echo "PAIR_VERIFIED=$_pair"; echo "HANDSHAKE_SCHEMA=${_hand_schema:-UNVERIFIED}"; echo "HANDSHAKE_ACK_ID=${_ack_id:-NONE}"; echo "HANDSHAKE_AGE_SEC=$_hand_age"
    echo "SNAPSHOT_GENERATION=$_generation"; echo "SNAPSHOT_FRESH=YES"
    echo "SHARED_INTELLIGENCE=GEMINI_PRIMARY_PLUS_ONE_HERMES_DEPUTY"; echo "GEMINI_INTELLIGENCE_SCOPE=PRIMARY_HIGHEST_FULL_REASONING_STRATEGY"; echo "HERMES_INTELLIGENCE_SCOPE=ONE_HERMES_FULL_DEPUTY_LOCAL_PLUS_CLOUD"
    echo "GEMINI_REASONING_LIMIT=NO_DIRECT_SYSFS"; echo "HERMES_TEACHER_LOOP=CONTINUITY_MEMORY_OUTCOME_FEEDBACK"; echo "HERMES_CLOUD_POLICY=ON_DEMAND_NEURON_GUARDED"; echo "OPTIMIZATION_OBJECTIVE=FRAME_STABILITY_FIRST_MINIMUM_POWER_SECOND"
    echo "GEMINI_CONNECTION=$_gem_connection"; echo "HERMES_CONNECTION=$_hermes_connection"
    echo "GEMINI_KEY_COUNT=$_gem_count"; echo "GEMINI_READY_COUNT=$_gem_ready"; echo "GEMINI_COOLDOWN_COUNT=$_gem_cd"; echo "HERMES_AUTH=$_hauth"
    echo "HERMES_CLOUD=ONE_HERMES_CLOUD_COGNITION"; echo "HERMES_CLOUD_ROLE=STRONGEST_HERMES_CLOUD_BRAIN_ON_DEMAND"; echo "HERMES_BACKEND_PRIORITY=LOCAL_CONTINUITY_THEN_CLOUD_ESCALATION_WHEN_NEEDED"; echo "WORKLOAD_FINAL=ADAPTIVE_CLASSIFIER_V2"; echo "DUAL_REGISTRY=SEPARATE"; echo "PREEXEC_WORKLOAD_GUARD=ACTIVE_LOCAL_GATED"
    echo "__STRATEGY_RESULT__"; echo "VALIDATION=$_cons_state"; echo "READBACK=$_readback"; echo "OUTCOME=$_outcome_last"; echo "OUTCOME_REASON=$(pub_clean "$_outcome_reason")"; echo "SHADOW=$_shadow_state"
    echo "__ENV__"; [ -r "$_learn" ] && cat "$_learn"
    echo "__HTTP__"; [ -r "$_gem_state" ] && cat "$_gem_state" || true
    echo "__SERVER__"; [ -r "$_hermes_state" ] && cat "$_hermes_state" || true
    echo "__DECISIONS__"
    echo "__PLANS__"; [ -n "$_plan_line" ] && echo "$_plan_line"
    echo "__FRAME__"; echo "$_frame_line"
    echo "__LOG__"; [ -r "$_root/runtime/events.log" ] && tail -n 80 "$_root/runtime/events.log" || true
    echo "__NETWORK__"; echo "SESSION_ACTIVE=0"; echo "QUALITY=UNMEASURED"
    echo "__REASONING__"; echo "STATE=$_cons_state"
    echo "__RESYNC__"; echo "STATE=$([ "$_pair" = YES ] && echo VERIFIED || echo UNVERIFIED)"; echo "CONTRACT=DJAEGER_AI_ADAPTIVE_V2"; echo "ACK_ID=${_ack_id:-NONE}"; echo "GENERATION=$_generation"
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
}
