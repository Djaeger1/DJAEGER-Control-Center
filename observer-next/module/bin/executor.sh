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

  _rtmp="$RESTORE_DIAG.tmp.$"
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
  _e="$(kv EPOCH "$SNAP")"; num "$_e" || return 1
  _age=$(( $(date +%s) - _e ))
  [ "$_age" -ge 0 ] && [ "$_age" -le 12 ]
}

frame_fresh(){
  [ "$(kv FRAME_EVIDENCE "$SNAP")" = VALID ] || return 1
  _f="$(kv FRAME_AT "$SNAP")"; num "$_f" || return 1
  _age=$(( $(date +%s) - _f ))
  [ "$_age" -ge 0 ] && [ "$_age" -le 20 ]
}

thermal_safe(){
  _skin="$(kv SKIN_TEMP_C "$SNAP")"; _bat="$(kv BATTERY_TEMP_C "$SNAP")"; _cpu="$(kv CPU_TEMP_C "$SNAP")"; _gpu="$(kv GPU_TEMP_C "$SNAP")"
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
  [ "$(kv EXECUTOR_ALLOWED "$APPROVAL")" = YES ] || { GATE_REASON=APPROVAL_DENIED; return 1; }
  [ "$(kv SHADOW_STATE "$SHADOW")" = PASS ] || { GATE_REASON=SHADOW_NOT_PASS; return 1; }
  _d="$(kv CANDIDATE_DIGEST "$APPROVAL")"
  [ -n "$_d" ] && [ "$_d" = "$(kv CANDIDATE_DIGEST "$POLICY")" ] && [ "$_d" = "$(kv CANDIDATE_DIGEST "$SHADOW")" ] || { GATE_REASON=DIGEST_MISMATCH; return 1; }
  [ "$(kv PACKAGE "$APPROVAL")" = "$(kv PACKAGE "$POLICY")" ] || { GATE_REASON=APPROVAL_PACKAGE_MISMATCH; return 1; }
  _pi="$(kv INTENT "$POLICY")"; [ -n "$_pi" ] || _pi=FRAME_FIRST_BALANCED
  _ai="$(kv INTENT "$APPROVAL")"; [ -n "$_ai" ] || _ai=FRAME_FIRST_BALANCED
  [ "$_ai" = "$_pi" ] || { GATE_REASON=APPROVAL_INTENT_MISMATCH; return 1; }
  ACTUATORS="$(kv ACTUATORS "$POLICY")"; [ -n "$ACTUATORS" ] || ACTUATORS=ALL
  _aa="$(kv ACTUATORS "$APPROVAL")"; [ -n "$_aa" ] || _aa=ALL
  valid_actuators "$ACTUATORS" || { GATE_REASON=INVALID_ACTUATOR_MASK; return 1; }
  [ "$_aa" = "$ACTUATORS" ] || { GATE_REASON=APPROVAL_ACTUATOR_MISMATCH; return 1; }
  _exp="$(kv EXPIRES_AT "$APPROVAL")"; num "$_exp" && [ "$_exp" -ge "$(date +%s)" ] || { GATE_REASON=APPROVAL_EXPIRED; return 1; }
  [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" = GAME ] || { GATE_REASON=NON_GAME; return 1; }
  [ "$(kv PACKAGE "$WORKLOAD")" = "$(kv PACKAGE "$POLICY")" ] && [ "$(kv ACTIVE_PACKAGE "$SNAP")" = "$(kv PACKAGE "$POLICY")" ] || { GATE_REASON=PACKAGE_MISMATCH; return 1; }
  snapshot_fresh || { GATE_REASON=STALE_SNAPSHOT; return 1; }
  frame_fresh || { GATE_REASON=FRAME_EVIDENCE_STALE; return 1; }
  thermal_safe || { GATE_REASON=THERMAL_GUARD; return 1; }

  LP="$(kv LITTLE_POLICY_PATH "$SNAP")"; BP="$(kv BIG_POLICY_PATH "$SNAP")"; GP="$(kv GPU_DEVFREQ_PATH "$SNAP")"
  valid_cpu "$LP" && valid_cpu "$BP" && valid_gpu "$GP" || { GATE_REASON=PATH_REJECTED; return 1; }

  LMIN="$(kv LITTLE_MIN_KHZ "$POLICY")"; LMAX="$(kv LITTLE_MAX_KHZ "$POLICY")"
  BMIN="$(kv BIG_MIN_KHZ "$POLICY")"; BMAX="$(kv BIG_MAX_KHZ "$POLICY")"
  GMIN="$(kv GPU_MIN_HZ "$POLICY")"; GMAX="$(kv GPU_MAX_HZ "$POLICY")"
  for _v in "$LMIN" "$LMAX" "$BMIN" "$BMAX" "$GMIN" "$GMAX"; do num "$_v" || { GATE_REASON=NON_NUMERIC; return 1; }; done
  [ "$(kv LITTLE_MIN_KHZ "$APPROVAL")" = "$LMIN" ] &&
  [ "$(kv LITTLE_MAX_KHZ "$APPROVAL")" = "$LMAX" ] &&
  [ "$(kv BIG_MIN_KHZ "$APPROVAL")" = "$BMIN" ] &&
  [ "$(kv BIG_MAX_KHZ "$APPROVAL")" = "$BMAX" ] &&
  [ "$(kv GPU_MIN_HZ "$APPROVAL")" = "$GMIN" ] &&
  [ "$(kv GPU_MAX_HZ "$APPROVAL")" = "$GMAX" ] || { GATE_REASON=APPROVAL_POLICY_MISMATCH; return 1; }
  contains_freq "$LMIN" "$(kv LITTLE_AVAILABLE_KHZ "$SNAP")" && contains_freq "$LMAX" "$(kv LITTLE_AVAILABLE_KHZ "$SNAP")" || { GATE_REASON=LITTLE_OPP_REJECTED; return 1; }
  contains_freq "$BMIN" "$(kv BIG_AVAILABLE_KHZ "$SNAP")" && contains_freq "$BMAX" "$(kv BIG_AVAILABLE_KHZ "$SNAP")" || { GATE_REASON=BIG_OPP_REJECTED; return 1; }
  contains_freq "$GMIN" "$(kv GPU_AVAILABLE_HZ "$SNAP")" && contains_freq "$GMAX" "$(kv GPU_AVAILABLE_HZ "$SNAP")" || { GATE_REASON=GPU_OPP_REJECTED; return 1; }

  GATE_DIGEST="$_d"; GATE_REASON=PASS
  return 0
}

apply_all(){
  _tmp="$BACKUP.tmp.$$"
  {
    echo "ACTUATORS=$ACTUATORS"
    echo "LITTLE_PATH=$LP"; echo "LITTLE_MIN=$(readv "$LP/scaling_min_freq")"; echo "LITTLE_MAX=$(readv "$LP/scaling_max_freq")"
    echo "BIG_PATH=$BP"; echo "BIG_MIN=$(readv "$BP/scaling_min_freq")"; echo "BIG_MAX=$(readv "$BP/scaling_max_freq")"
    echo "GPU_PATH=$GP"; echo "GPU_MIN=$(readv "$GP/min_freq")"; echo "GPU_MAX=$(readv "$GP/max_freq")"
  } > "$_tmp"
  chmod 600 "$_tmp"; mv -f "$_tmp" "$BACKUP"

  if act_has "$ACTUATORS" LITTLE; then pair_apply "$LP" scaling_min_freq scaling_max_freq "$LMIN" "$LMAX" || return 1; fi
  if act_has "$ACTUATORS" BIG; then pair_apply "$BP" scaling_min_freq scaling_max_freq "$BMIN" "$BMAX" || return 1; fi
  if act_has "$ACTUATORS" GPU; then pair_apply "$GP" min_freq max_freq "$GMIN" "$GMAX" || return 1; fi

  ACTIVE_DIGEST="$GATE_DIGEST"
  APPLIED_PACKAGE="$(kv PACKAGE "$POLICY")"
  APPLIED_INTENT="$(kv INTENT "$POLICY")"; [ -n "$APPLIED_INTENT" ] || APPLIED_INTENT=FRAME_FIRST_BALANCED
  APPLIED_ACTUATORS="$ACTUATORS"
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

active_readback_ok(){
  if act_has "$ACTUATORS" LITTLE; then
    [ "$(readv "$LP/scaling_min_freq")" = "$LMIN" ] && [ "$(readv "$LP/scaling_max_freq")" = "$LMAX" ] || return 1
  fi
  if act_has "$ACTUATORS" BIG; then
    [ "$(readv "$BP/scaling_min_freq")" = "$BMIN" ] && [ "$(readv "$BP/scaling_max_freq")" = "$BMAX" ] || return 1
  fi
  if act_has "$ACTUATORS" GPU; then
    [ "$(readv "$GP/min_freq")" = "$GMIN" ] && [ "$(readv "$GP/max_freq")" = "$GMAX" ] || return 1
  fi
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
    record_outcome KEPT "POST_APPLY_STABLE_${APPLIED_INTENT}" "$APPLIED_PACKAGE" "$ACTIVE_DIGEST"
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
    publish ROLLED_BACK "$_reason"
    return 0
  fi
  READBACK=RESTORE_FAILED
  record_outcome ROLLBACK_FAILED "$_reason" "$_pkg" "$_digest" "$_little" "$_big" "$_gpu"
  publish ROLLBACK_FAILED "$_reason"
  return 1
}

reconcile(){
  load_active

  # A failed restore is a hard fail-closed latch. Repeated writes can fight the
  # kernel/thermal owner and create an endless CANDIDATE_SWITCH loop.
  if [ "$PREV_EXECUTOR_STATE" = ROLLBACK_FAILED ] && [ -r "$BACKUP" ]; then
    READBACK=RESTORE_FAILED
    ROLLBACK_STATE=RESTORE_FAILED
    publish ROLLBACK_FAILED RESTORE_FAILURE_LATCHED
    return 1
  fi

  if gate; then
    if [ "$ACTIVE_DIGEST" = "$GATE_DIGEST" ] && [ -r "$BACKUP" ]; then
      if ! active_readback_ok; then
        READBACK=DRIFT
        rollback_active SYSFS_DRIFT
        return 1
      fi
      if ! post_apply_monitor; then
        READBACK=VERIFIED
        rollback_active POST_APPLY_REGRESSION
        return 1
      fi
      READBACK=VERIFIED
      publish APPLIED ACTIVE_APPROVAL
      return 0
    fi

    if [ "$ACTIVE_DIGEST" != NONE ] || [ -r "$BACKUP" ]; then
      _old_pkg="$APPLIED_PACKAGE"; _old_digest="$ACTIVE_DIGEST"; _old_little="$APPLIED_LITTLE"; _old_big="$APPLIED_BIG"; _old_gpu="$APPLIED_GPU"
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

    _failed_pkg="$(kv PACKAGE "$POLICY")"; _failed_digest="$GATE_DIGEST"
    if restore_all; then
      record_outcome ROLLED_BACK APPLY_OR_READBACK_FAILED "$_failed_pkg" "$_failed_digest"
      READBACK=RESTORED
      publish ROLLED_BACK APPLY_OR_READBACK_FAILED
    else
      record_outcome ROLLBACK_FAILED APPLY_OR_READBACK_FAILED "$_failed_pkg" "$_failed_digest"
      READBACK=RESTORE_FAILED
      publish ROLLBACK_FAILED APPLY_OR_READBACK_FAILED
    fi
    return 1
  fi

  if [ "$ACTIVE_DIGEST" != NONE ] || [ -r "$BACKUP" ]; then
    rollback_active "$GATE_REASON"
  else
    ACTIVE_DIGEST=NONE; APPLIED_PACKAGE=NONE; APPLIED_INTENT=NONE; APPLIED_ACTUATORS=NONE; APPLIED_LITTLE=NA; APPLIED_BIG=NA; APPLIED_GPU=NA; READBACK=NA; ROLLBACK_STATE=STANDBY
    publish IDLE "$GATE_REASON"
  fi
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
  daemon)
    trap 'load_active; if [ "$PREV_EXECUTOR_STATE" != ROLLBACK_FAILED ] && { [ "$ACTIVE_DIGEST" != NONE ] || [ -r "$BACKUP" ]; }; then rollback_active SERVICE_STOP >/dev/null 2>&1 || true; fi; exit 0' INT TERM
    while :; do reconcile >/dev/null 2>&1 || true; sleep 2; done
    ;;
  *) echo "usage: executor.sh ROOT {once|recover|daemon}"; exit 2 ;;
esac
