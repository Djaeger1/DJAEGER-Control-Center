#!/system/bin/sh
# Internal hardware transaction worker of AI Agent.
# AI Agent is the controller; this file only performs its gated SYSFS write/readback/rollback transactions.
ROOT="$1"
MODE="${2:-daemon}"
BIN_DIR="${0%/*}"
if [ "$MODE" = daemon ] && [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim executor
fi
SYSROOT="${DJAEGER_SYSFS_ROOT:-}"
SNAP="$ROOT/runtime/snapshot.env"
WORKLOAD="$ROOT/runtime/workload.env"
POLICY="$ROOT/policy/candidate.env"
SHADOW="$ROOT/runtime/shadow.env"
APPROVAL="$ROOT/policy/approved.env"
STATE="$ROOT/runtime/execution.env"
BACKUP="$ROOT/runtime/execution_backup.env"
MONITOR="$ROOT/runtime/execution_monitor.env"
OUTCOMES="$ROOT/history/outcomes.csv"
OUTCOME_MARK="$ROOT/runtime/execution_outcome.mark"
RESTORE_DIAG="$ROOT/runtime/execution_restore.env"
SUPPRESS="$ROOT/runtime/execution_suppress.env"
LEARN="$ROOT/history/learned_envelope.env"
MODEFILE="$ROOT/config/execution_mode"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
num(){ case "$1" in ''|*[!0-9]*) return 1;; *) return 0;; esac; }
map_path(){ [ -n "$SYSROOT" ] && printf '%s%s' "$SYSROOT" "$1" || printf '%s' "$1"; }
readv(){ _f="$(map_path "$1")"; [ -r "$_f" ] && cat "$_f" 2>/dev/null | head -n1; }
writev(){
  _f="$(map_path "$1")"
  [ -w "$_f" ] || return 1

  # qcom-cpufreq-hw can return a non-zero write status even when the requested
  # policy value is actually committed. Device truth is the immediate readback,
  # not the shell write return code.
  printf '%s\n' "$2" > "$_f" 2>/dev/null
  _wr=$?
  _rb="$(cat "$_f" 2>/dev/null | head -n1)"
  [ "$_rb" = "$2" ] && return 0
  [ "$_wr" -eq 0 ] || return 1
  return 1
}
valid_cpu(){ case "$1" in /sys/devices/system/cpu/cpufreq/policy[0-9]|/sys/devices/system/cpu/cpufreq/policy[0-9][0-9]) return 0;; *) return 1;; esac; }
valid_gpu(){ case "$1" in /sys/class/kgsl/kgsl-3d0/devfreq|/sys/class/devfreq/*gpu*|/sys/class/devfreq/*mali*) return 0;; *) return 1;; esac; }
contains_freq(){ _v="$1"; _list="$2"; for _x in $_list; do [ "$_x" = "$_v" ] && return 0; done; return 1; }
act_has(){
  _mask="$1"; _axis="$2"
  [ "$_mask" = ALL ] && return 0
  case ",$_mask," in
    *,"$_axis",*) return 0 ;;
    *) return 1 ;;
  esac
}
valid_actuators(){
  case "$1" in
    ALL|LITTLE|BIG|GPU|LITTLE,BIG|LITTLE,GPU|BIG,GPU|LITTLE,BIG,GPU) return 0 ;;
    *) return 1 ;;
  esac
}
clean_csv(){ printf '%s' "$1" | tr '\r\n,' '   ' | tr -cd 'A-Za-z0-9._:+/%= @-'; }

suppress_digest(){
  _sd="$1"; _sp="$2"; _sr="$3"; _secs="${4:-120}"
  num "$_secs" || _secs=120
  _stmp="$SUPPRESS.tmp.$PPID"
  {
    echo "DIGEST=$_sd"
    echo "PACKAGE=$_sp"
    echo "REASON=$_sr"
    echo "UNTIL=$(( $(date +%s) + _secs ))"
  } > "$_stmp"
  chmod 600 "$_stmp"; mv -f "$_stmp" "$SUPPRESS"
}

digest_suppressed(){
  _sd="$1"; _sp="$2"
  [ -r "$SUPPRESS" ] || return 1
  _du="$(kv UNTIL "$SUPPRESS")"; num "$_du" || { rm -f "$SUPPRESS"; return 1; }
  if [ "$_du" -lt "$(date +%s)" ] 2>/dev/null; then
    rm -f "$SUPPRESS"
    return 1
  fi
  [ "$(kv DIGEST "$SUPPRESS")" = "$_sd" ] &&
  [ "$(kv PACKAGE "$SUPPRESS")" = "$_sp" ]
}

record_outcome(){
  _result="$1"; _reason="$2"; _pkg="$3"; _digest="$4"
  _olittle="$5"; _obig="$6"; _ogpu="$7"
  [ -n "$_pkg" ] || _pkg=NONE
  [ -n "$_digest" ] || _digest=NONE
  [ -n "$_olittle" ] || _olittle="$APPLIED_LITTLE"
  [ -n "$_obig" ] || _obig="$APPLIED_BIG"
  [ -n "$_ogpu" ] || _ogpu="$APPLIED_GPU"
  _sig="$_digest|$_result|$_reason"
  [ "$(cat "$OUTCOME_MARK" 2>/dev/null)" = "$_sig" ] && return 0
  mkdir -p "$ROOT/history" 2>/dev/null
  [ -f "$OUTCOMES" ] || echo "epoch,package,digest,result,reason,fps,jank,p95_ms,power_mw,readback,little,big,gpu" > "$OUTCOMES"
  # Preserve CSV row boundaries even if an older/interrupted writer left EOF
  # without a terminating newline. A fused row breaks validation supersession.
  if [ -s "$OUTCOMES" ] && ! tail -c 1 "$OUTCOMES" 2>/dev/null | grep -q "^$"; then
    printf '\n' >> "$OUTCOMES"
  fi
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$(date +%s)" "$(clean_csv "$_pkg")" "$(clean_csv "$_digest")" "$(clean_csv "$_result")" "$(clean_csv "$_reason")" \
    "$(clean_csv "$(kv FPS_EST "$SNAP")")" "$(clean_csv "$(kv JANK_PCT "$SNAP")")" "$(clean_csv "$(kv P95_MS "$SNAP")")" "$(clean_csv "$(kv POWER_MW "$SNAP")")" \
    "$(clean_csv "$READBACK")" "$(clean_csv "$_olittle")" "$(clean_csv "$_obig")" "$(clean_csv "$_ogpu")" >> "$OUTCOMES"
  chmod 600 "$OUTCOMES"
  printf '%s\n' "$_sig" > "$OUTCOME_MARK"; chmod 600 "$OUTCOME_MARK"
}

publish(){
  _tmp="$STATE.tmp.$$"
  {
    echo "EXECUTOR_STATE=$1"
    echo "EXECUTOR_REASON=$2"
    echo "ACTIVE_DIGEST=${ACTIVE_DIGEST:-NONE}"
    echo "APPLIED_PACKAGE=${APPLIED_PACKAGE:-NONE}"
    echo "APPLIED_INTENT=${APPLIED_INTENT:-NONE}"
    echo "APPLIED_ACTUATORS=${APPLIED_ACTUATORS:-NONE}"
    echo "APPLIED_LITTLE=${APPLIED_LITTLE:-NA}"
    echo "APPLIED_BIG=${APPLIED_BIG:-NA}"
    echo "APPLIED_GPU=${APPLIED_GPU:-NA}"
    echo "READBACK=${READBACK:-NA}"
    echo "ROLLBACK_STATE=${ROLLBACK_STATE:-NA}"
    echo "APPLIED_AT=${APPLIED_AT:-0}"
    echo "MONITOR_BAD_COUNT=${MONITOR_BAD_COUNT:-0}"
    echo "MONITOR_SAMPLES=${MONITOR_SAMPLES:-0}"
    echo "UPDATED_AT=$(date +%s)"
  } > "$_tmp"
  chmod 600 "$_tmp"; mv -f "$_tmp" "$STATE"
}

pair_apply(){
  _path="$1"; _minfile="$2"; _maxfile="$3"; _tmin="$4"; _tmax="$5"
  _curmin="$(readv "$_path/$_minfile")"; _curmax="$(readv "$_path/$_maxfile")"
  num "$_curmin" && num "$_curmax" && num "$_tmin" && num "$_tmax" || return 1
  [ "$_tmin" -le "$_tmax" ] || return 1
  if [ "$_tmin" -gt "$_curmax" ]; then
    writev "$_path/$_maxfile" "$_tmax" && writev "$_path/$_minfile" "$_tmin" || return 1
  elif [ "$_tmax" -lt "$_curmin" ]; then
    writev "$_path/$_minfile" "$_tmin" && writev "$_path/$_maxfile" "$_tmax" || return 1
  else
    writev "$_path/$_maxfile" "$_tmax" && writev "$_path/$_minfile" "$_tmin" || return 1
  fi
  [ "$(readv "$_path/$_minfile")" = "$_tmin" ] && [ "$(readv "$_path/$_maxfile")" = "$_tmax" ]
}

pair_restore(){ pair_apply "$1" "$2" "$3" "$4" "$5"; }

restore_all(){
  [ -r "$BACKUP" ] || { ROLLBACK_STATE=NO_BACKUP; return 0; }

  LP="$(kv LITTLE_PATH "$BACKUP")"; BP="$(kv BIG_PATH "$BACKUP")"; GP="$(kv GPU_PATH "$BACKUP")"
  _ltmin="$(kv LITTLE_MIN "$BACKUP")"; _ltmax="$(kv LITTLE_MAX "$BACKUP")"
  _btmin="$(kv BIG_MIN "$BACKUP")"; _btmax="$(kv BIG_MAX "$BACKUP")"
  _gtmin="$(kv GPU_MIN "$BACKUP")"; _gtmax="$(kv GPU_MAX "$BACKUP")"

  _restore_act="$(kv ACTUATORS "$BACKUP")"; [ -n "$_restore_act" ] || _restore_act=ALL
  valid_actuators "$_restore_act" || { ROLLBACK_STATE=RESTORE_FAILED; return 1; }

  _ok=1
  _ls=SKIP; _bs=SKIP; _gs=SKIP

  if act_has "$_restore_act" LITTLE; then
    if valid_cpu "$LP" && pair_restore "$LP" scaling_min_freq scaling_max_freq "$_ltmin" "$_ltmax"; then _ls=OK; else _ls=FAIL; _ok=0; fi
  fi
  if act_has "$_restore_act" BIG; then
    if valid_cpu "$BP" && pair_restore "$BP" scaling_min_freq scaling_max_freq "$_btmin" "$_btmax"; then _bs=OK; else _bs=FAIL; _ok=0; fi
  fi
  if act_has "$_restore_act" GPU; then
    if valid_gpu "$GP" && pair_restore "$GP" min_freq max_freq "$_gtmin" "$_gtmax"; then _gs=OK; else _gs=FAIL; _ok=0; fi
  fi

  _rtmp="$RESTORE_DIAG.tmp.$PPID"
  {
    echo "UPDATED_AT=$(date +%s)"
    echo "ACTUATORS=$_restore_act"
    echo "LITTLE_STATUS=$_ls"
    echo "LITTLE_TARGET=$_ltmin-$_ltmax"
    echo "LITTLE_READBACK=$(readv "$LP/scaling_min_freq")-$(readv "$LP/scaling_max_freq")"
    echo "BIG_STATUS=$_bs"
    echo "BIG_TARGET=$_btmin-$_btmax"
    echo "BIG_READBACK=$(readv "$BP/scaling_min_freq")-$(readv "$BP/scaling_max_freq")"
    echo "GPU_STATUS=$_gs"
    echo "GPU_TARGET=$_gtmin-$_gtmax"
    echo "GPU_READBACK=$(readv "$GP/min_freq")-$(readv "$GP/max_freq")"
  } > "$_rtmp"
  chmod 600 "$_rtmp"; mv -f "$_rtmp" "$RESTORE_DIAG"

  if [ "$_ok" = 1 ]; then
    rm -f "$BACKUP" "$MONITOR"
    ACTIVE_DIGEST=NONE; APPLIED_PACKAGE=NONE; APPLIED_INTENT=NONE; APPLIED_ACTUATORS=NONE; APPLIED_LITTLE=NA; APPLIED_BIG=NA; APPLIED_GPU=NA
    APPLIED_AT=0; MONITOR_BAD_COUNT=0; MONITOR_SAMPLES=0
    ROLLBACK_STATE=RESTORED
    return 0
  fi

  # Fail closed and preserve BACKUP + exact diagnostics. Do not hammer sysfs
  # every 2 seconds; reconcile() latches this state until an explicit recovery.
  ROLLBACK_STATE=RESTORE_FAILED
  return 1
}

snapshot_fresh(){
  _src="${1:-$SNAP}"
  _e="$(kv EPOCH "$_src")"; num "$_e" || return 1
  _age=$(( $(date +%s) - _e ))
  [ "$_age" -ge 0 ] && [ "$_age" -le 12 ]
}

frame_fresh(){
  _src="${1:-$SNAP}"
  [ "$(kv FRAME_EVIDENCE "$_src")" = VALID ] || return 1
  _f="$(kv FRAME_AT "$_src")"; num "$_f" || return 1
  _age=$(( $(date +%s) - _f ))
  [ "$_age" -ge 0 ] && [ "$_age" -le 20 ]
}

thermal_safe(){
  _src="${1:-$SNAP}"
  _skin="$(kv SKIN_TEMP_C "$_src")"; _bat="$(kv BATTERY_TEMP_C "$_src")"; _cpu="$(kv CPU_TEMP_C "$_src")"; _gpu="$(kv GPU_TEMP_C "$_src")"
  awk -v s="$_skin" -v b="$_bat" -v c="$_cpu" -v g="$_gpu" 'BEGIN{
    if(s!~/^[0-9]+([.][0-9]+)?$/||b!~/^[0-9]+([.][0-9]+)?$/||c!~/^[0-9]+([.][0-9]+)?$/) exit 1;
    gok=(g!~/^[0-9]+([.][0-9]+)?$/ || g<75);
    # 44C is a pressure point, not a hard execution ban. Hard stop is aligned
    # with candidate validation; reconcile() rechecks every ~2s and rolls back.
    exit !((s<46)&&(b<45)&&(c<75)&&gok)
  }'
}

gate(){
  [ "$(cat "$MODEFILE" 2>/dev/null)" = AUTO ] || { GATE_REASON=MODE_OFF; return 1; }
  [ -r "$APPROVAL" ] && [ -r "$POLICY" ] && [ -r "$SHADOW" ] || { GATE_REASON=APPROVAL_MISSING; return 1; }

  _POLICY="$ROOT/runtime/.executor_policy.$PPID"
  _APPROVAL="$ROOT/runtime/.executor_approval.$PPID"
  _SHADOW="$ROOT/runtime/.executor_shadow.$PPID"
  _SNAP="$ROOT/runtime/.executor_snapshot.$PPID"
  _WORKLOAD="$ROOT/runtime/.executor_workload.$PPID"

  cp "$POLICY" "$_POLICY" 2>/dev/null &&
  cp "$APPROVAL" "$_APPROVAL" 2>/dev/null &&
  cp "$SHADOW" "$_SHADOW" 2>/dev/null &&
  cp "$SNAP" "$_SNAP" 2>/dev/null &&
  cp "$WORKLOAD" "$_WORKLOAD" 2>/dev/null || { GATE_REASON=COHERENT_SNAPSHOT_FAILED; return 1; }

  [ "$(kv EXECUTOR_ALLOWED "$_APPROVAL")" = YES ] || { GATE_REASON=APPROVAL_DENIED; return 1; }
  [ "$(kv SHADOW_STATE "$_SHADOW")" = PASS ] || { GATE_REASON=SHADOW_NOT_PASS; return 1; }

  _d="$(kv CANDIDATE_DIGEST "$_APPROVAL")"
  [ -n "$_d" ] &&
  [ "$_d" = "$(kv CANDIDATE_DIGEST "$_POLICY")" ] &&
  [ "$_d" = "$(kv CANDIDATE_DIGEST "$_SHADOW")" ] || { GATE_REASON=DIGEST_MISMATCH; return 1; }

  GATE_PACKAGE="$(kv PACKAGE "$_POLICY")"
  [ -n "$GATE_PACKAGE" ] || { GATE_REASON=PACKAGE_MISSING; return 1; }
  [ "$(kv PACKAGE "$_APPROVAL")" = "$GATE_PACKAGE" ] || { GATE_REASON=APPROVAL_PACKAGE_MISMATCH; return 1; }

  GATE_INTENT="$(kv INTENT "$_POLICY")"; [ -n "$GATE_INTENT" ] || GATE_INTENT=FRAME_FIRST_BALANCED
  _ai="$(kv INTENT "$_APPROVAL")"; [ -n "$_ai" ] || _ai=FRAME_FIRST_BALANCED
  [ "$_ai" = "$GATE_INTENT" ] || { GATE_REASON=APPROVAL_INTENT_MISMATCH; return 1; }

  GATE_ACTUATORS="$(kv ACTUATORS "$_POLICY")"; [ -n "$GATE_ACTUATORS" ] || GATE_ACTUATORS=ALL
  _aa="$(kv ACTUATORS "$_APPROVAL")"; [ -n "$_aa" ] || _aa=ALL
  valid_actuators "$GATE_ACTUATORS" || { GATE_REASON=INVALID_ACTUATOR_MASK; return 1; }
  [ "$_aa" = "$GATE_ACTUATORS" ] || { GATE_REASON=APPROVAL_ACTUATOR_MISMATCH; return 1; }

  _exp="$(kv EXPIRES_AT "$_APPROVAL")"; num "$_exp" && [ "$_exp" -ge "$(date +%s)" ] || { GATE_REASON=APPROVAL_EXPIRED; return 1; }
  [ "$(kv WORKLOAD_CLASS "$_WORKLOAD")" = GAME ] || { GATE_REASON=NON_GAME; return 1; }
  [ "$(kv PACKAGE "$_WORKLOAD")" = "$GATE_PACKAGE" ] &&
  [ "$(kv ACTIVE_PACKAGE "$_SNAP")" = "$GATE_PACKAGE" ] || { GATE_REASON=PACKAGE_MISMATCH; return 1; }

  snapshot_fresh "$_SNAP" || { GATE_REASON=STALE_SNAPSHOT; return 1; }
  frame_fresh "$_SNAP" || { GATE_REASON=FRAME_EVIDENCE_STALE; return 1; }
  thermal_safe "$_SNAP" || { GATE_REASON=THERMAL_GUARD; return 1; }

  LP="$(kv LITTLE_POLICY_PATH "$_SNAP")"; BP="$(kv BIG_POLICY_PATH "$_SNAP")"; GP="$(kv GPU_DEVFREQ_PATH "$_SNAP")"
  valid_cpu "$LP" && valid_cpu "$BP" && valid_gpu "$GP" || { GATE_REASON=PATH_REJECTED; return 1; }

  LMIN="$(kv LITTLE_MIN_KHZ "$_POLICY")"; LMAX="$(kv LITTLE_MAX_KHZ "$_POLICY")"
  BMIN="$(kv BIG_MIN_KHZ "$_POLICY")"; BMAX="$(kv BIG_MAX_KHZ "$_POLICY")"
  GMIN="$(kv GPU_MIN_HZ "$_POLICY")"; GMAX="$(kv GPU_MAX_HZ "$_POLICY")"

  for _v in "$LMIN" "$LMAX" "$BMIN" "$BMAX" "$GMIN" "$GMAX"; do
    num "$_v" || { GATE_REASON=NON_NUMERIC; return 1; }
  done

  [ "$(kv LITTLE_MIN_KHZ "$_APPROVAL")" = "$LMIN" ] &&
  [ "$(kv LITTLE_MAX_KHZ "$_APPROVAL")" = "$LMAX" ] &&
  [ "$(kv BIG_MIN_KHZ "$_APPROVAL")" = "$BMIN" ] &&
  [ "$(kv BIG_MAX_KHZ "$_APPROVAL")" = "$BMAX" ] &&
  [ "$(kv GPU_MIN_HZ "$_APPROVAL")" = "$GMIN" ] &&
  [ "$(kv GPU_MAX_HZ "$_APPROVAL")" = "$GMAX" ] || { GATE_REASON=APPROVAL_POLICY_MISMATCH; return 1; }

  contains_freq "$LMIN" "$(kv LITTLE_AVAILABLE_KHZ "$_SNAP")" &&
  contains_freq "$LMAX" "$(kv LITTLE_AVAILABLE_KHZ "$_SNAP")" || { GATE_REASON=LITTLE_OPP_REJECTED; return 1; }
  contains_freq "$BMIN" "$(kv BIG_AVAILABLE_KHZ "$_SNAP")" &&
  contains_freq "$BMAX" "$(kv BIG_AVAILABLE_KHZ "$_SNAP")" || { GATE_REASON=BIG_OPP_REJECTED; return 1; }
  contains_freq "$GMIN" "$(kv GPU_AVAILABLE_HZ "$_SNAP")" &&
  contains_freq "$GMAX" "$(kv GPU_AVAILABLE_HZ "$_SNAP")" || { GATE_REASON=GPU_OPP_REJECTED; return 1; }

  ACTUATORS="$GATE_ACTUATORS"
  GATE_DIGEST="$_d"
  if digest_suppressed "$GATE_DIGEST" "$GATE_PACKAGE"; then
    _sreason="$(kv REASON "$SUPPRESS")"
    case "$_sreason" in
      POST_APPLY_REGRESSION) GATE_REASON=RECENT_POST_APPLY_REGRESSION ;;
      APPLY_OR_READBACK_FAILED) GATE_REASON=RECENT_APPLY_OR_READBACK_FAILED ;;
      THERMAL_GUARD) GATE_REASON=RECENT_THERMAL_GUARD ;;
      *) GATE_REASON=RECENT_EXTERNAL_OVERRIDE ;;
    esac
    return 1
  fi
  GATE_REASON=PASS
  return 0
}
apply_all(){
  _tmp="$BACKUP.tmp.$$"
  {
    echo "ACTUATORS=$GATE_ACTUATORS"
    echo "LITTLE_PATH=$LP"; echo "LITTLE_MIN=$(readv "$LP/scaling_min_freq")"; echo "LITTLE_MAX=$(readv "$LP/scaling_max_freq")"
    echo "BIG_PATH=$BP"; echo "BIG_MIN=$(readv "$BP/scaling_min_freq")"; echo "BIG_MAX=$(readv "$BP/scaling_max_freq")"
    echo "GPU_PATH=$GP"; echo "GPU_MIN=$(readv "$GP/min_freq")"; echo "GPU_MAX=$(readv "$GP/max_freq")"
  } > "$_tmp"
  chmod 600 "$_tmp"; mv -f "$_tmp" "$BACKUP"

  if act_has "$GATE_ACTUATORS" LITTLE; then pair_apply "$LP" scaling_min_freq scaling_max_freq "$LMIN" "$LMAX" || return 1; fi
  if act_has "$GATE_ACTUATORS" BIG; then pair_apply "$BP" scaling_min_freq scaling_max_freq "$BMIN" "$BMAX" || return 1; fi
  if act_has "$GATE_ACTUATORS" GPU; then pair_apply "$GP" min_freq max_freq "$GMIN" "$GMAX" || return 1; fi

  ACTIVE_DIGEST="$GATE_DIGEST"
  APPLIED_PACKAGE="$GATE_PACKAGE"
  APPLIED_INTENT="$GATE_INTENT"
  APPLIED_ACTUATORS="$GATE_ACTUATORS"
  APPLIED_LITTLE="$(readv "$LP/scaling_min_freq")-$(readv "$LP/scaling_max_freq")"
  APPLIED_BIG="$(readv "$BP/scaling_min_freq")-$(readv "$BP/scaling_max_freq")"
  APPLIED_GPU="$(readv "$GP/min_freq")-$(readv "$GP/max_freq")"
  READBACK=VERIFIED; ROLLBACK_STATE=ARMED
  APPLIED_AT=$(date +%s); MONITOR_BAD_COUNT=0; MONITOR_SAMPLES=0
  _mtmp="$(mktemp "${MONITOR}.tmp.XXXXXX" 2>/dev/null)"; [ -n "$_mtmp" ] || _mtmp="${MONITOR}.tmp.$(date +%s).0"
  {
    echo "DIGEST=$ACTIVE_DIGEST"
    echo "BAD_COUNT=0"
    echo "SAMPLES=0"
  } > "$_mtmp"; chmod 600 "$_mtmp"; mv -f "$_mtmp" "$MONITOR"
  return 0
}

load_active(){
  PREV_EXECUTOR_STATE="$(kv EXECUTOR_STATE "$STATE")"; [ -n "$PREV_EXECUTOR_STATE" ] || PREV_EXECUTOR_STATE=UNKNOWN
  PREV_EXECUTOR_REASON="$(kv EXECUTOR_REASON "$STATE")"; [ -n "$PREV_EXECUTOR_REASON" ] || PREV_EXECUTOR_REASON=UNKNOWN
  ACTIVE_DIGEST="$(kv ACTIVE_DIGEST "$STATE")"; [ -n "$ACTIVE_DIGEST" ] || ACTIVE_DIGEST=NONE
  APPLIED_PACKAGE="$(kv APPLIED_PACKAGE "$STATE")"; [ -n "$APPLIED_PACKAGE" ] || APPLIED_PACKAGE=NONE
  APPLIED_INTENT="$(kv APPLIED_INTENT "$STATE")"; [ -n "$APPLIED_INTENT" ] || APPLIED_INTENT=FRAME_FIRST_BALANCED
  APPLIED_ACTUATORS="$(kv APPLIED_ACTUATORS "$STATE")"; [ -n "$APPLIED_ACTUATORS" ] || APPLIED_ACTUATORS=ALL
  APPLIED_LITTLE="$(kv APPLIED_LITTLE "$STATE")"; [ -n "$APPLIED_LITTLE" ] || APPLIED_LITTLE=NA
  APPLIED_BIG="$(kv APPLIED_BIG "$STATE")"; [ -n "$APPLIED_BIG" ] || APPLIED_BIG=NA
  APPLIED_GPU="$(kv APPLIED_GPU "$STATE")"; [ -n "$APPLIED_GPU" ] || APPLIED_GPU=NA
  READBACK="$(kv READBACK "$STATE")"; [ -n "$READBACK" ] || READBACK=NA
  ROLLBACK_STATE="$(kv ROLLBACK_STATE "$STATE")"; [ -n "$ROLLBACK_STATE" ] || ROLLBACK_STATE=NA
  APPLIED_AT="$(kv APPLIED_AT "$STATE")"; case "$APPLIED_AT" in ''|*[!0-9]*) APPLIED_AT=0;; esac
  MONITOR_BAD_COUNT="$(kv BAD_COUNT "$MONITOR")"; case "$MONITOR_BAD_COUNT" in ''|*[!0-9]*) MONITOR_BAD_COUNT=0;; esac
  MONITOR_SAMPLES="$(kv SAMPLES "$MONITOR")"; case "$MONITOR_SAMPLES" in ''|*[!0-9]*) MONITOR_SAMPLES=0;; esac
}

active_context_safe(){
  [ "$(cat "$MODEFILE" 2>/dev/null)" = AUTO ] || { ACTIVE_GUARD_REASON=MODE_OFF; return 1; }
  [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" = GAME ] || { ACTIVE_GUARD_REASON=NON_GAME; return 1; }
  [ "$(kv PACKAGE "$WORKLOAD")" = "$APPLIED_PACKAGE" ] &&
  [ "$(kv ACTIVE_PACKAGE "$SNAP")" = "$APPLIED_PACKAGE" ] || { ACTIVE_GUARD_REASON=PACKAGE_MISMATCH; return 1; }

  snapshot_fresh "$SNAP" || { ACTIVE_GUARD_REASON=STALE_SNAPSHOT; return 1; }
  frame_fresh "$SNAP" || { ACTIVE_GUARD_REASON=FRAME_EVIDENCE_STALE; return 1; }
  thermal_safe "$SNAP" || { ACTIVE_GUARD_REASON=THERMAL_GUARD; return 1; }

  LP="$(kv LITTLE_PATH "$BACKUP")"; BP="$(kv BIG_PATH "$BACKUP")"; GP="$(kv GPU_PATH "$BACKUP")"
  valid_cpu "$LP" && valid_cpu "$BP" && valid_gpu "$GP" || { ACTIVE_GUARD_REASON=PATH_REJECTED; return 1; }
  valid_actuators "$APPLIED_ACTUATORS" || { ACTIVE_GUARD_REASON=INVALID_ACTUATOR_MASK; return 1; }

  ACTIVE_GUARD_REASON=PASS
  return 0
}

active_readback_state(){
  LP="$(kv LITTLE_PATH "$BACKUP")"; BP="$(kv BIG_PATH "$BACKUP")"; GP="$(kv GPU_PATH "$BACKUP")"
  valid_cpu "$LP" && valid_cpu "$BP" && valid_gpu "$GP" || return 2
  valid_actuators "$APPLIED_ACTUATORS" || return 2

  ACTIVE_NATIVE_RELAXED=0
  ACTIVE_EFFECTIVE_LITTLE="$APPLIED_LITTLE"

  _almin="${APPLIED_LITTLE%%-*}"; _almax="${APPLIED_LITTLE#*-}"
  _abmin="${APPLIED_BIG%%-*}"; _abmax="${APPLIED_BIG#*-}"
  _agmin="${APPLIED_GPU%%-*}"; _agmax="${APPLIED_GPU#*-}"

  if act_has "$APPLIED_ACTUATORS" LITTLE; then
    _cmin="$(readv "$LP/scaling_min_freq")"; _cmax="$(readv "$LP/scaling_max_freq")"
    num "$_cmin" && num "$_cmax" || return 2
    if [ "$_cmin" = "$_almin" ] && [ "$_cmax" = "$_almax" ]; then
      :
    else
      # Qualcomm/MIUI power control may relax a raised LITTLE min_freq back
      # toward the pre-transaction floor while preserving the exact max_freq.
      # Accept only that bounded, power-saving direction. Never tolerate a
      # changed max, a min below the backup floor, or a more aggressive min.
      _blmin="$(kv LITTLE_MIN "$BACKUP")"; _blmax="$(kv LITTLE_MAX "$BACKUP")"
      num "$_blmin" && num "$_blmax" || return 2
      if [ "$_blmax" = "$_almax" ] &&
         [ "$_cmax" = "$_almax" ] &&
         [ "$_cmin" -ge "$_blmin" ] 2>/dev/null &&
         [ "$_cmin" -le "$_almin" ] 2>/dev/null; then
        ACTIVE_NATIVE_RELAXED=1
        ACTIVE_EFFECTIVE_LITTLE="${_cmin}-${_cmax}"
      else
        return 1
      fi
    fi
  fi
  if act_has "$APPLIED_ACTUATORS" BIG; then
    _cmin="$(readv "$BP/scaling_min_freq")"; _cmax="$(readv "$BP/scaling_max_freq")"
    num "$_cmin" && num "$_cmax" || return 2
    [ "$_cmin" = "$_abmin" ] && [ "$_cmax" = "$_abmax" ] || return 1
  fi
  if act_has "$APPLIED_ACTUATORS" GPU; then
    _cmin="$(readv "$GP/min_freq")"; _cmax="$(readv "$GP/max_freq")"
    num "$_cmin" && num "$_cmax" || return 2
    [ "$_cmin" = "$_agmin" ] && [ "$_cmax" = "$_agmax" ] || return 1
  fi
  return 0
}

active_readback_ok(){
  active_readback_state
  [ "$?" -eq 0 ]
}

pair_post_restore_state(){
  _path="$1"; _minfile="$2"; _maxfile="$3"; _applied="$4"; _bmin="$5"; _bmax="$6"
  _cmin="$(readv "$_path/$_minfile")"; _cmax="$(readv "$_path/$_maxfile")"
  num "$_cmin" && num "$_cmax" || { echo UNREADABLE; return 0; }
  [ "$_cmin" -le "$_cmax" ] 2>/dev/null || { echo INVALID; return 0; }
  _amin="${_applied%%-*}"; _amax="${_applied#*-}"
  if [ "$_cmin" = "$_bmin" ] && [ "$_cmax" = "$_bmax" ]; then
    echo BACKUP
  elif [ "$_cmin" = "$_amin" ] && [ "$_cmax" = "$_amax" ]; then
    echo APPLIED
  else
    echo EXTERNAL
  fi
}

resolve_restore_failure(){
  # Use a dedicated name: record_outcome() also uses the global shell variable
  # "_reason", so reusing it here mutates our caller reason in /system/bin/sh.
  _resolve_reason="$1"; _pkg="$2"; _digest="$3"; _little="$4"; _big="$5"; _gpu="$6"
  [ -r "$BACKUP" ] || return 1

  LP="$(kv LITTLE_PATH "$BACKUP")"; BP="$(kv BIG_PATH "$BACKUP")"; GP="$(kv GPU_PATH "$BACKUP")"
  _ltmin="$(kv LITTLE_MIN "$BACKUP")"; _ltmax="$(kv LITTLE_MAX "$BACKUP")"
  _btmin="$(kv BIG_MIN "$BACKUP")"; _btmax="$(kv BIG_MAX "$BACKUP")"
  _gtmin="$(kv GPU_MIN "$BACKUP")"; _gtmax="$(kv GPU_MAX "$BACKUP")"
  _act="$(kv ACTUATORS "$BACKUP")"; [ -n "$_act" ] || _act="$APPLIED_ACTUATORS"
  valid_actuators "$_act" || return 1

  _ls=SKIP; _bs=SKIP; _gs=SKIP; _external=0; _blocked=0
  if act_has "$_act" LITTLE; then
    _ls="$(pair_post_restore_state "$LP" scaling_min_freq scaling_max_freq "$_little" "$_ltmin" "$_ltmax")"
    case "$_ls" in EXTERNAL) _external=1;; APPLIED|UNREADABLE|INVALID) _blocked=1;; esac
  fi
  if act_has "$_act" BIG; then
    _bs="$(pair_post_restore_state "$BP" scaling_min_freq scaling_max_freq "$_big" "$_btmin" "$_btmax")"
    case "$_bs" in EXTERNAL) _external=1;; APPLIED|UNREADABLE|INVALID) _blocked=1;; esac
  fi
  if act_has "$_act" GPU; then
    _gs="$(pair_post_restore_state "$GP" min_freq max_freq "$_gpu" "$_gtmin" "$_gtmax")"
    case "$_gs" in EXTERNAL) _external=1;; APPLIED|UNREADABLE|INVALID) _blocked=1;; esac
  fi

  _rtmp="$RESTORE_DIAG.tmp.$PPID"
  {
    echo "UPDATED_AT=$(date +%s)"
    echo "ACTUATORS=$_act"
    echo "FAILURE_REASON=$_resolve_reason"
    echo "LITTLE_POST_STATE=$_ls"
    echo "LITTLE_READBACK=$(readv "$LP/scaling_min_freq")-$(readv "$LP/scaling_max_freq")"
    echo "BIG_POST_STATE=$_bs"
    echo "BIG_READBACK=$(readv "$BP/scaling_min_freq")-$(readv "$BP/scaling_max_freq")"
    echo "GPU_POST_STATE=$_gs"
    echo "GPU_READBACK=$(readv "$GP/min_freq")-$(readv "$GP/max_freq")"
  } > "$_rtmp"
  chmod 600 "$_rtmp"; mv -f "$_rtmp" "$RESTORE_DIAG"

  [ "$_blocked" -eq 0 ] || return 1

  if [ "$_external" -eq 1 ]; then
    READBACK=EXTERNAL_OVERRIDE
    ROLLBACK_STATE=RELINQUISHED
    record_outcome RELEASED "${_resolve_reason}_EXTERNAL_OVERRIDE" "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"
    suppress_digest "$_digest" "$_pkg" "${_resolve_reason}_EXTERNAL_OVERRIDE" 900
  else
    READBACK=RESTORED
    ROLLBACK_STATE=RESTORED
    record_outcome ROLLED_BACK "${_resolve_reason}_READBACK_RECOVERED" "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"
  fi

  rm -f "$BACKUP" "$MONITOR"
  ACTIVE_DIGEST=NONE; APPLIED_PACKAGE=NONE; APPLIED_INTENT=NONE; APPLIED_ACTUATORS=NONE
  APPLIED_LITTLE=NA; APPLIED_BIG=NA; APPLIED_GPU=NA; APPLIED_AT=0
  MONITOR_BAD_COUNT=0; MONITOR_SAMPLES=0
  publish IDLE "${_resolve_reason}_RESOLVED"
  return 0
}
post_apply_monitor(){
  _now=$(date +%s)
  [ "$APPLIED_AT" -gt 0 ] 2>/dev/null || return 0
  [ $((_now-APPLIED_AT)) -ge 15 ] || return 0
  [ -r "$LEARN" ] || return 0
  [ "$(kv PACKAGE "$LEARN")" = "$APPLIED_PACKAGE" ] || return 0
  _fps="$(kv FPS_EST "$SNAP")"; _jank="$(kv JANK_PCT "$SNAP")"; _p95="$(kv P95_MS "$SNAP")"; _power="$(kv POWER_MW "$SNAP")"
  _bfps="$(kv FPS_P50 "$LEARN")"; _bjank="$(kv JANK_P95 "$LEARN")"; _bp95="$(kv FRAME_P95_P95_MS "$LEARN")"
  _bpower50="$(kv POWER_P50_MW "$LEARN")"; _bpower95="$(kv POWER_P95_MW "$LEARN")"
  _intent="$APPLIED_INTENT"; [ -n "$_intent" ] || _intent=FRAME_FIRST_BALANCED
  _bad=0
  awk -v intent="$_intent" -v f="$_fps" -v bf="$_bfps" -v j="$_jank" -v bj="$_bjank" -v p="$_p95" -v bp="$_bp95" -v w="$_power" -v p50="$_bpower50" -v p95="$_bpower95" 'BEGIN{
    if(f!~/^[0-9]+([.][0-9]+)?$/ || p!~/^[0-9]+([.][0-9]+)?$/ || bf<=0 || bp<=0) exit 2;
    bad=(f<bf*0.95 || p>bp*1.10);
    if(j~/^[0-9]+([.][0-9]+)?$/ && bj>0 && j>bj*1.20+1) bad=1;
    if(w~/^[0-9]+([.][0-9]+)?$/){
      if(intent=="POWER_EFFICIENCY" && p50>0 && w>p50*1.10) bad=1;
      else if(intent=="FRAME_RECOVERY" && p95>0 && w>p95*1.10) bad=1;
      else if(intent!="FRAME_RECOVERY" && intent!="POWER_EFFICIENCY" && p95>0 && w>p95*1.05) bad=1;
    }
    exit bad?1:0
  }'
  _rc=$?
  [ "$_rc" -eq 2 ] && return 0
  MONITOR_SAMPLES=$((MONITOR_SAMPLES+1))
  if [ "$_rc" -eq 1 ]; then MONITOR_BAD_COUNT=$((MONITOR_BAD_COUNT+1)); else MONITOR_BAD_COUNT=0; fi
  _mtmp="$(mktemp "${MONITOR}.tmp.XXXXXX" 2>/dev/null)"; [ -n "$_mtmp" ] || _mtmp="${MONITOR}.tmp.${_now}.${MONITOR_SAMPLES}"
  {
    echo "DIGEST=$ACTIVE_DIGEST"
    echo "BAD_COUNT=$MONITOR_BAD_COUNT"
    echo "SAMPLES=$MONITOR_SAMPLES"
    echo "UPDATED_AT=$_now"
  } > "$_mtmp"; chmod 600 "$_mtmp"; mv -f "$_mtmp" "$MONITOR"
  if [ "$MONITOR_SAMPLES" -eq 5 ] && [ "$MONITOR_BAD_COUNT" -eq 0 ]; then
    _kept_little="$APPLIED_LITTLE"
    [ "${ACTIVE_NATIVE_RELAXED:-0}" -eq 1 ] 2>/dev/null && _kept_little="$ACTIVE_EFFECTIVE_LITTLE"
    record_outcome KEPT "POST_APPLY_STABLE_${APPLIED_INTENT}" "$APPLIED_PACKAGE" "$ACTIVE_DIGEST" "$_kept_little" "$APPLIED_BIG" "$APPLIED_GPU"
  fi
  [ "$MONITOR_BAD_COUNT" -lt 3 ] || return 1
  return 0
}

rollback_active(){
  _reason="$1"
  _pkg="$APPLIED_PACKAGE"; _digest="$ACTIVE_DIGEST"
  _little="$APPLIED_LITTLE"; _big="$APPLIED_BIG"; _gpu="$APPLIED_GPU"
  if restore_all; then
    READBACK=RESTORED
    record_outcome ROLLED_BACK "$_reason" "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"
    case "$_reason" in
      THERMAL_GUARD)
        suppress_digest "$_digest" "$_pkg" THERMAL_GUARD 180
        ;;
      POST_APPLY_REGRESSION)
        # A candidate that measurably worsened frame/power behavior must not
        # be retried immediately. Quarantine it for the full candidate
        # freshness horizon so a new digest/evidence is required.
        suppress_digest "$_digest" "$_pkg" POST_APPLY_REGRESSION 900
        ;;
    esac
    publish ROLLED_BACK "$_reason"
    return 0
  fi

  # A restore can race native thermal/kernel ownership. Re-read every owned
  # axis before declaring a hard failure. If no DJAEGER-applied value remains
  # and every readback is valid, the rollback was either completed or ownership
  # was externally superseded; do not latch and do not hammer sysfs again.
  if resolve_restore_failure "$_reason" "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"; then
    return 0
  fi

  READBACK=RESTORE_FAILED
  record_outcome ROLLBACK_FAILED "$_reason" "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"
  publish ROLLBACK_FAILED "$_reason"
  return 1
}

release_external_override(){
  _pkg="$APPLIED_PACKAGE"; _digest="$ACTIVE_DIGEST"
  _little="$APPLIED_LITTLE"; _big="$APPLIED_BIG"; _gpu="$APPLIED_GPU"

  # First classify every owned axis before writing anything. Native power/
  # thermal control may take one policy while another still exactly matches
  # DJAEGER. Knowing the whole transaction state up front prevents ordering
  # artifacts (for example LITTLE restore failing before BIG is seen external).
  LP="$(kv LITTLE_PATH "$BACKUP")"; BP="$(kv BIG_PATH "$BACKUP")"; GP="$(kv GPU_PATH "$BACKUP")"
  _ltmin="$(kv LITTLE_MIN "$BACKUP")"; _ltmax="$(kv LITTLE_MAX "$BACKUP")"
  _btmin="$(kv BIG_MIN "$BACKUP")"; _btmax="$(kv BIG_MAX "$BACKUP")"
  _gtmin="$(kv GPU_MIN "$BACKUP")"; _gtmax="$(kv GPU_MAX "$BACKUP")"
  _act="$(kv ACTUATORS "$BACKUP")"; [ -n "$_act" ] || _act="$APPLIED_ACTUATORS"
  valid_actuators "$_act" || return 1

  _ok=1; _external=0
  _lpre=SKIP; _bpre=SKIP; _gpre=SKIP
  _ls=SKIP; _bs=SKIP; _gs=SKIP

  if act_has "$_act" LITTLE; then
    _lpre="$(pair_post_restore_state "$LP" scaling_min_freq scaling_max_freq "$_little" "$_ltmin" "$_ltmax")"
    case "$_lpre" in EXTERNAL) _external=1;; BACKUP|APPLIED) :;; *) _ok=0;; esac
  fi
  if act_has "$_act" BIG; then
    _bpre="$(pair_post_restore_state "$BP" scaling_min_freq scaling_max_freq "$_big" "$_btmin" "$_btmax")"
    case "$_bpre" in EXTERNAL) _external=1;; BACKUP|APPLIED) :;; *) _ok=0;; esac
  fi
  if act_has "$_act" GPU; then
    _gpre="$(pair_post_restore_state "$GP" min_freq max_freq "$_gpu" "$_gtmin" "$_gtmax")"
    case "$_gpre" in EXTERNAL) _external=1;; BACKUP|APPLIED) :;; *) _ok=0;; esac
  fi

  if [ "$_ok" -eq 1 ] && act_has "$_act" LITTLE; then
    case "$_lpre" in
      BACKUP) _ls=ALREADY_BACKUP ;;
      EXTERNAL) _ls=RELINQUISHED ;;
      APPLIED)
        if pair_restore "$LP" scaling_min_freq scaling_max_freq "$_ltmin" "$_ltmax"; then
          _ls=RESTORED
        else
          _post="$(pair_post_restore_state "$LP" scaling_min_freq scaling_max_freq "$_little" "$_ltmin" "$_ltmax")"
          case "$_post" in
            BACKUP) _ls=RESTORED_AFTER_RACE ;;
            EXTERNAL) _ls=RELINQUISHED_AFTER_RACE; _external=1 ;;
            APPLIED)
              if [ "$_external" -eq 1 ]; then
                _ls=RELINQUISHED_APPLIED_AFTER_EXTERNAL_RACE
              else
                _ls=FAIL_AFTER_RESTORE_APPLIED; _ok=0
              fi ;;
            *) _ls="FAIL_AFTER_RESTORE_$_post"; _ok=0 ;;
          esac
        fi ;;
    esac
  fi

  if [ "$_ok" -eq 1 ] && act_has "$_act" BIG; then
    case "$_bpre" in
      BACKUP) _bs=ALREADY_BACKUP ;;
      EXTERNAL) _bs=RELINQUISHED ;;
      APPLIED)
        if pair_restore "$BP" scaling_min_freq scaling_max_freq "$_btmin" "$_btmax"; then
          _bs=RESTORED
        else
          _post="$(pair_post_restore_state "$BP" scaling_min_freq scaling_max_freq "$_big" "$_btmin" "$_btmax")"
          case "$_post" in
            BACKUP) _bs=RESTORED_AFTER_RACE ;;
            EXTERNAL) _bs=RELINQUISHED_AFTER_RACE; _external=1 ;;
            APPLIED)
              if [ "$_external" -eq 1 ]; then
                _bs=RELINQUISHED_APPLIED_AFTER_EXTERNAL_RACE
              else
                _bs=FAIL_AFTER_RESTORE_APPLIED; _ok=0
              fi ;;
            *) _bs="FAIL_AFTER_RESTORE_$_post"; _ok=0 ;;
          esac
        fi ;;
    esac
  fi

  if [ "$_ok" -eq 1 ] && act_has "$_act" GPU; then
    case "$_gpre" in
      BACKUP) _gs=ALREADY_BACKUP ;;
      EXTERNAL) _gs=RELINQUISHED ;;
      APPLIED)
        if pair_restore "$GP" min_freq max_freq "$_gtmin" "$_gtmax"; then
          _gs=RESTORED
        else
          _post="$(pair_post_restore_state "$GP" min_freq max_freq "$_gpu" "$_gtmin" "$_gtmax")"
          case "$_post" in
            BACKUP) _gs=RESTORED_AFTER_RACE ;;
            EXTERNAL) _gs=RELINQUISHED_AFTER_RACE; _external=1 ;;
            APPLIED)
              if [ "$_external" -eq 1 ]; then
                _gs=RELINQUISHED_APPLIED_AFTER_EXTERNAL_RACE
              else
                _gs=FAIL_AFTER_RESTORE_APPLIED; _ok=0
              fi ;;
            *) _gs="FAIL_AFTER_RESTORE_$_post"; _ok=0 ;;
          esac
        fi ;;
    esac
  fi

  _rtmp="$RESTORE_DIAG.tmp.$PPID"
  {
    echo "UPDATED_AT=$(date +%s)"
    echo "ACTUATORS=$_act"
    echo "RELEASE_REASON=SYSFS_EXTERNAL_OVERRIDE"
    echo "LITTLE_PRE_STATE=$_lpre"
    echo "LITTLE_STATUS=$_ls"
    echo "LITTLE_READBACK=$(readv "$LP/scaling_min_freq")-$(readv "$LP/scaling_max_freq")"
    echo "BIG_PRE_STATE=$_bpre"
    echo "BIG_STATUS=$_bs"
    echo "BIG_READBACK=$(readv "$BP/scaling_min_freq")-$(readv "$BP/scaling_max_freq")"
    echo "GPU_PRE_STATE=$_gpre"
    echo "GPU_STATUS=$_gs"
    echo "GPU_READBACK=$(readv "$GP/min_freq")-$(readv "$GP/max_freq")"
  } > "$_rtmp"
  chmod 600 "$_rtmp"; mv -f "$_rtmp" "$RESTORE_DIAG"

  if [ "$_ok" -ne 1 ]; then
    READBACK=RESTORE_FAILED
    ROLLBACK_STATE=RESTORE_FAILED
    record_outcome ROLLBACK_FAILED SYSFS_EXTERNAL_OVERRIDE_CLEANUP "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"
    suppress_digest "$_digest" "$_pkg" SYSFS_EXTERNAL_OVERRIDE_CLEANUP 180
    publish ROLLBACK_FAILED EXTERNAL_OVERRIDE_CLEANUP_FAILED
    return 1
  fi

  READBACK=EXTERNAL_OVERRIDE
  ROLLBACK_STATE=RELINQUISHED
  record_outcome RELEASED SYSFS_EXTERNAL_OVERRIDE "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"
  suppress_digest "$_digest" "$_pkg" SYSFS_EXTERNAL_OVERRIDE 900

  rm -f "$BACKUP" "$MONITOR"
  ACTIVE_DIGEST=NONE
  APPLIED_PACKAGE=NONE
  APPLIED_INTENT=NONE
  APPLIED_ACTUATORS=NONE
  APPLIED_LITTLE=NA
  APPLIED_BIG=NA
  APPLIED_GPU=NA
  APPLIED_AT=0
  MONITOR_BAD_COUNT=0
  MONITOR_SAMPLES=0

  publish IDLE SYSFS_EXTERNAL_OVERRIDE
  return 0
}

relinquish_no_write(){
  _pkg="$APPLIED_PACKAGE"; _digest="$ACTIVE_DIGEST"
  _little="$APPLIED_LITTLE"; _big="$APPLIED_BIG"; _gpu="$APPLIED_GPU"
  [ -r "$BACKUP" ] || return 1

  LP="$(kv LITTLE_PATH "$BACKUP")"; BP="$(kv BIG_PATH "$BACKUP")"; GP="$(kv GPU_PATH "$BACKUP")"
  _act="$(kv ACTUATORS "$BACKUP")"; [ -n "$_act" ] || _act="$APPLIED_ACTUATORS"

  _rtmp="$RESTORE_DIAG.tmp.$PPID"
  {
    echo "UPDATED_AT=$(date +%s)"
    echo "ACTUATORS=$_act"
    echo "RELEASE_REASON=EXPLICIT_NO_WRITE_RELINQUISH"
    echo "LITTLE_STATUS=RELINQUISHED_NO_WRITE"
    echo "LITTLE_READBACK=$(readv "$LP/scaling_min_freq")-$(readv "$LP/scaling_max_freq")"
    echo "BIG_STATUS=RELINQUISHED_NO_WRITE"
    echo "BIG_READBACK=$(readv "$BP/scaling_min_freq")-$(readv "$BP/scaling_max_freq")"
    echo "GPU_STATUS=RELINQUISHED_NO_WRITE"
    echo "GPU_READBACK=$(readv "$GP/min_freq")-$(readv "$GP/max_freq")"
  } > "$_rtmp"
  chmod 600 "$_rtmp"; mv -f "$_rtmp" "$RESTORE_DIAG"

  READBACK=EXTERNAL_OVERRIDE
  ROLLBACK_STATE=RELINQUISHED
  record_outcome RELEASED SYSFS_EXTERNAL_OVERRIDE "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"
  suppress_digest "$_digest" "$_pkg" SYSFS_EXTERNAL_OVERRIDE 900
  rm -f "$BACKUP" "$MONITOR"
  ACTIVE_DIGEST=NONE; APPLIED_PACKAGE=NONE; APPLIED_INTENT=NONE; APPLIED_ACTUATORS=NONE
  APPLIED_LITTLE=NA; APPLIED_BIG=NA; APPLIED_GPU=NA; APPLIED_AT=0
  MONITOR_BAD_COUNT=0; MONITOR_SAMPLES=0
  publish IDLE SYSFS_EXTERNAL_OVERRIDE
  return 0
}

reconcile(){
  load_active

  # A failed restore is a hard fail-closed latch. Repeated writes can fight the
  # kernel/thermal owner and create an endless recovery loop.
  if [ "$PREV_EXECUTOR_STATE" = ROLLBACK_FAILED ] && [ -r "$BACKUP" ]; then
    READBACK=RESTORE_FAILED
    ROLLBACK_STATE=RESTORE_FAILED
    publish ROLLBACK_FAILED RESTORE_FAILURE_LATCHED
    return 1
  fi

  _gate_ready=0

  # Once a transaction is applied, pin that exact digest long enough to measure
  # the result. Candidate churn or a temporary approval gap must not abort the
  # live trial. Only device-truth safety, SYSFS drift or measured regression can
  # roll it back before a KEEP decision.
  if [ "$ACTIVE_DIGEST" != NONE ] && [ -r "$BACKUP" ]; then
    active_readback_state
    _rb_state=$?
    if [ "$_rb_state" -eq 1 ]; then
      READBACK=DRIFT
      release_external_override
      return 1
    elif [ "$_rb_state" -eq 2 ]; then
      READBACK=UNAVAILABLE
      ROLLBACK_STATE=ARMED
      publish APPLIED READBACK_UNAVAILABLE
      return 1
    fi

    if [ "${ACTIVE_NATIVE_RELAXED:-0}" -eq 1 ] 2>/dev/null; then
      READBACK=NATIVE_RELAXED
    else
      READBACK=VERIFIED
    fi

    if ! active_context_safe; then
      rollback_active "$ACTIVE_GUARD_REASON"
      return 1
    fi

    if ! post_apply_monitor; then
      READBACK=VERIFIED
      rollback_active POST_APPLY_REGRESSION
      return 1
    fi

    if [ "${ACTIVE_NATIVE_RELAXED:-0}" -eq 1 ] 2>/dev/null; then
      READBACK=NATIVE_RELAXED
    else
      READBACK=VERIFIED
    fi
    _now="$(date +%s)"
    _active_age=$((_now-APPLIED_AT))

    if [ "$MONITOR_SAMPLES" -lt 5 ] 2>/dev/null || [ "$_active_age" -lt 25 ] 2>/dev/null; then
      publish APPLIED ACTIVE_TRIAL_PINNED
      return 0
    fi

    # The current transaction has accumulated enough stable samples to qualify
    # for KEEP. Only now may a different fully-approved candidate supersede it.
    if gate; then
      if [ "$GATE_DIGEST" = "$ACTIVE_DIGEST" ]; then
        publish APPLIED KEPT_ACTIVE
        return 0
      fi

      _old_pkg="$APPLIED_PACKAGE"; _old_digest="$ACTIVE_DIGEST"
      _old_little="$APPLIED_LITTLE"; _old_big="$APPLIED_BIG"; _old_gpu="$APPLIED_GPU"

      if ! restore_all; then
        READBACK=RESTORE_FAILED
        record_outcome ROLLBACK_FAILED CANDIDATE_SWITCH_AFTER_KEEP "$_old_pkg" "$_old_digest" "$_old_little" "$_old_big" "$_old_gpu"
        publish ROLLBACK_FAILED CANDIDATE_SWITCH_AFTER_KEEP_RESTORE_FAILED
        return 1
      fi

      READBACK=RESTORED
      record_outcome SUPERSEDED CANDIDATE_SWITCH_AFTER_KEEP "$_old_pkg" "$_old_digest" "$_old_little" "$_old_big" "$_old_gpu"
      _gate_ready=1
    else
      publish APPLIED KEPT_ACTIVE
      return 0
    fi
  fi

  if [ "$_gate_ready" -ne 1 ]; then
    if gate; then
      _gate_ready=1
    else
      if [ "$ACTIVE_DIGEST" != NONE ] || [ -r "$BACKUP" ]; then
        rollback_active "$GATE_REASON"
      else
        ACTIVE_DIGEST=NONE; APPLIED_PACKAGE=NONE; APPLIED_INTENT=NONE; APPLIED_ACTUATORS=NONE
        APPLIED_LITTLE=NA; APPLIED_BIG=NA; APPLIED_GPU=NA; READBACK=NA; ROLLBACK_STATE=STANDBY
        publish IDLE "$GATE_REASON"
      fi
      return 1
    fi
  fi

  if [ "$ACTIVE_DIGEST" != NONE ] || [ -r "$BACKUP" ]; then
    _old_pkg="$APPLIED_PACKAGE"; _old_digest="$ACTIVE_DIGEST"
    _old_little="$APPLIED_LITTLE"; _old_big="$APPLIED_BIG"; _old_gpu="$APPLIED_GPU"
    _switch_reason=CANDIDATE_SWITCH
    [ "$_old_digest" = NONE ] && _switch_reason=STALE_BACKUP_RECOVERY

    if ! restore_all; then
      READBACK=RESTORE_FAILED
      record_outcome ROLLBACK_FAILED "$_switch_reason" "$_old_pkg" "$_old_digest" "$_old_little" "$_old_big" "$_old_gpu"
      publish ROLLBACK_FAILED "${_switch_reason}_RESTORE_FAILED"
      return 1
    fi

    READBACK=RESTORED
    record_outcome ROLLED_BACK "$_switch_reason" "$_old_pkg" "$_old_digest" "$_old_little" "$_old_big" "$_old_gpu"
  fi

  if apply_all; then
    if active_readback_ok; then
      READBACK=VERIFIED
      record_outcome APPLIED_VERIFIED CONSENSUS_SHADOW_APPROVED "$APPLIED_PACKAGE" "$ACTIVE_DIGEST"
      publish APPLIED CONSENSUS_SHADOW_APPROVED
      return 0
    fi
    READBACK=DRIFT
  else
    READBACK=FAILED
  fi

  _failed_pkg="$GATE_PACKAGE"; _failed_digest="$GATE_DIGEST"
  _failed_little="${LMIN}-${LMAX}"
  _failed_big="${BMIN}-${BMAX}"
  _failed_gpu="${GMIN}-${GMAX}"

  if restore_all; then
    READBACK=RESTORED
    record_outcome ROLLED_BACK APPLY_OR_READBACK_FAILED "$_failed_pkg" "$_failed_digest" "$_failed_little" "$_failed_big" "$_failed_gpu"
    # A digest that could not be applied/read back cleanly must not be retried
    # every daemon tick. Quarantine only this digest; a newly learned digest
    # remains eligible immediately.
    suppress_digest "$_failed_digest" "$_failed_pkg" APPLY_OR_READBACK_FAILED 900
    publish ROLLED_BACK APPLY_OR_READBACK_FAILED
    return 1
  fi

  # A failed apply can be partial: some axes may already contain candidate
  # values while native power/thermal ownership moves others. Reclassify using
  # the intended candidate targets before creating a permanent restore latch.
  if resolve_restore_failure APPLY_OR_READBACK_FAILED "$_failed_pkg" "$_failed_digest" "$_failed_little" "$_failed_big" "$_failed_gpu"; then
    suppress_digest "$_failed_digest" "$_failed_pkg" APPLY_OR_READBACK_FAILED 900
    return 1
  fi

  READBACK=RESTORE_FAILED
  record_outcome ROLLBACK_FAILED APPLY_OR_READBACK_FAILED "$_failed_pkg" "$_failed_digest" "$_failed_little" "$_failed_big" "$_failed_gpu"
  publish ROLLBACK_FAILED APPLY_OR_READBACK_FAILED
  return 1
}
case "$MODE" in
  once) reconcile ;;
  recover)
    load_active
    if [ -r "$BACKUP" ]; then
      if restore_all; then
        READBACK=RESTORED
        publish ROLLED_BACK EXPLICIT_RECOVERY_OK
        exit 0
      else
        READBACK=RESTORE_FAILED
        publish ROLLBACK_FAILED EXPLICIT_RECOVERY_FAILED
        exit 1
      fi
    fi
    READBACK=NA; ROLLBACK_STATE=NO_BACKUP
    publish IDLE EXPLICIT_RECOVERY_NO_BACKUP
    ;;
  relinquish)
    # Explicit no-write recovery for a transaction whose owned SYSFS was
    # overridden by another kernel/vendor controller. This intentionally
    # discards the stale rollback backup and resumes from fresh Device Truth.
    load_active
    if [ -r "$BACKUP" ]; then
      relinquish_no_write
      exit 0
    fi
    READBACK=NA; ROLLBACK_STATE=NO_BACKUP
    publish IDLE EXPLICIT_RELINQUISH_NO_BACKUP
    ;;
  resolve-latched)
    # No-write forensic resolver for an existing RESTORE_FAILURE_LATCHED state.
    # It clears the latch only when every owned axis is readable and no axis
    # still equals DJAEGER's applied value.
    load_active
    if [ -r "$BACKUP" ]; then
      if resolve_restore_failure LATCHED_RECHECK "$APPLIED_PACKAGE" "$ACTIVE_DIGEST" "$APPLIED_LITTLE" "$APPLIED_BIG" "$APPLIED_GPU"; then
        exit 0
      fi
      READBACK=RESTORE_FAILED
      ROLLBACK_STATE=RESTORE_FAILED
      publish ROLLBACK_FAILED RESTORE_FAILURE_LATCHED
      exit 1
    fi
    READBACK=NA; ROLLBACK_STATE=NO_BACKUP
    publish IDLE EXPLICIT_RESOLVE_NO_BACKUP
    ;;
  daemon)
    trap 'load_active; if [ "$PREV_EXECUTOR_STATE" != ROLLBACK_FAILED ] && { [ "$ACTIVE_DIGEST" != NONE ] || [ -r "$BACKUP" ]; }; then LP="$(kv LITTLE_PATH "$BACKUP")"; BP="$(kv BIG_PATH "$BACKUP")"; GP="$(kv GPU_PATH "$BACKUP")"; if active_readback_ok; then rollback_active SERVICE_STOP >/dev/null 2>&1 || true; else release_external_override >/dev/null 2>&1 || true; fi; fi; exit 0' INT TERM
    while :; do reconcile >/dev/null 2>&1 || true; sleep 2; done
    ;;
  *) echo "usage: executor.sh ROOT {once|recover|relinquish|resolve-latched|daemon}"; exit 2 ;;
esac
