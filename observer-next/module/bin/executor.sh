#!/system/bin/sh
# DJAEGER AI adaptive local executor.
# Only this file may write approved CPU/GPU frequency bounds.
ROOT="$1"
MODE="${2:-daemon}"
SYSROOT="${DJAEGER_SYSFS_ROOT:-}"
SNAP="$ROOT/runtime/snapshot.env"
WORKLOAD="$ROOT/runtime/workload.env"
POLICY="$ROOT/policy/candidate.env"
SHADOW="$ROOT/runtime/shadow.env"
APPROVAL="$ROOT/policy/approved.env"
STATE="$ROOT/runtime/execution.env"
BACKUP="$ROOT/runtime/execution_backup.env"
MONITOR="$ROOT/runtime/execution_monitor.env"
LEARN="$ROOT/history/learned_envelope.env"
MODEFILE="$ROOT/config/execution_mode"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
num(){ case "$1" in ''|*[!0-9]*) return 1;; *) return 0;; esac; }
map_path(){ [ -n "$SYSROOT" ] && printf '%s%s' "$SYSROOT" "$1" || printf '%s' "$1"; }
readv(){ _f="$(map_path "$1")"; [ -r "$_f" ] && cat "$_f" 2>/dev/null | head -n1; }
writev(){ _f="$(map_path "$1")"; [ -w "$_f" ] || return 1; printf '%s\n' "$2" > "$_f"; }
valid_cpu(){ case "$1" in /sys/devices/system/cpu/cpufreq/policy[0-9]|/sys/devices/system/cpu/cpufreq/policy[0-9][0-9]) return 0;; *) return 1;; esac; }
valid_gpu(){ case "$1" in /sys/class/kgsl/kgsl-3d0/devfreq|/sys/class/devfreq/*gpu*|/sys/class/devfreq/*mali*) return 0;; *) return 1;; esac; }
contains_freq(){ _v="$1"; _list="$2"; for _x in $_list; do [ "$_x" = "$_v" ] && return 0; done; return 1; }

publish(){
  _tmp="$STATE.tmp.$$"
  {
    echo "EXECUTOR_STATE=$1"
    echo "EXECUTOR_REASON=$2"
    echo "ACTIVE_DIGEST=${ACTIVE_DIGEST:-NONE}"
    echo "APPLIED_PACKAGE=${APPLIED_PACKAGE:-NONE}"
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
  _ok=1
  valid_cpu "$LP" && pair_restore "$LP" scaling_min_freq scaling_max_freq "$(kv LITTLE_MIN "$BACKUP")" "$(kv LITTLE_MAX "$BACKUP")" || _ok=0
  valid_cpu "$BP" && pair_restore "$BP" scaling_min_freq scaling_max_freq "$(kv BIG_MIN "$BACKUP")" "$(kv BIG_MAX "$BACKUP")" || _ok=0
  valid_gpu "$GP" && pair_restore "$GP" min_freq max_freq "$(kv GPU_MIN "$BACKUP")" "$(kv GPU_MAX "$BACKUP")" || _ok=0
  if [ "$_ok" = 1 ]; then
    rm -f "$BACKUP" "$MONITOR"
    ACTIVE_DIGEST=NONE; APPLIED_PACKAGE=NONE; APPLIED_LITTLE=NA; APPLIED_BIG=NA; APPLIED_GPU=NA
    APPLIED_AT=0; MONITOR_BAD_COUNT=0; MONITOR_SAMPLES=0
    ROLLBACK_STATE=RESTORED
    return 0
  fi
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
    exit !((s<44)&&(b<43)&&(c<75)&&gok)
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
    echo "LITTLE_PATH=$LP"; echo "LITTLE_MIN=$(readv "$LP/scaling_min_freq")"; echo "LITTLE_MAX=$(readv "$LP/scaling_max_freq")"
    echo "BIG_PATH=$BP"; echo "BIG_MIN=$(readv "$BP/scaling_min_freq")"; echo "BIG_MAX=$(readv "$BP/scaling_max_freq")"
    echo "GPU_PATH=$GP"; echo "GPU_MIN=$(readv "$GP/min_freq")"; echo "GPU_MAX=$(readv "$GP/max_freq")"
  } > "$_tmp"
  chmod 600 "$_tmp"; mv -f "$_tmp" "$BACKUP"

  pair_apply "$LP" scaling_min_freq scaling_max_freq "$LMIN" "$LMAX" || return 1
  pair_apply "$BP" scaling_min_freq scaling_max_freq "$BMIN" "$BMAX" || return 1
  pair_apply "$GP" min_freq max_freq "$GMIN" "$GMAX" || return 1

  ACTIVE_DIGEST="$GATE_DIGEST"
  APPLIED_PACKAGE="$(kv PACKAGE "$POLICY")"
  APPLIED_LITTLE="$LMIN-$LMAX"; APPLIED_BIG="$BMIN-$BMAX"; APPLIED_GPU="$GMIN-$GMAX"
  READBACK=VERIFIED; ROLLBACK_STATE=ARMED
  APPLIED_AT=$(date +%s); MONITOR_BAD_COUNT=0; MONITOR_SAMPLES=0
  {
    echo "DIGEST=$ACTIVE_DIGEST"
    echo "BAD_COUNT=0"
    echo "SAMPLES=0"
  } > "$MONITOR.tmp.$"; chmod 600 "$MONITOR.tmp.$"; mv -f "$MONITOR.tmp.$" "$MONITOR"
  return 0
}

load_active(){
  ACTIVE_DIGEST="$(kv ACTIVE_DIGEST "$STATE")"; [ -n "$ACTIVE_DIGEST" ] || ACTIVE_DIGEST=NONE
  APPLIED_PACKAGE="$(kv APPLIED_PACKAGE "$STATE")"; [ -n "$APPLIED_PACKAGE" ] || APPLIED_PACKAGE=NONE
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
  [ "$(readv "$LP/scaling_min_freq")" = "$LMIN" ] &&
  [ "$(readv "$LP/scaling_max_freq")" = "$LMAX" ] &&
  [ "$(readv "$BP/scaling_min_freq")" = "$BMIN" ] &&
  [ "$(readv "$BP/scaling_max_freq")" = "$BMAX" ] &&
  [ "$(readv "$GP/min_freq")" = "$GMIN" ] &&
  [ "$(readv "$GP/max_freq")" = "$GMAX" ]
}

post_apply_monitor(){
  _now=$(date +%s)
  [ "$APPLIED_AT" -gt 0 ] 2>/dev/null || return 0
  [ $((_now-APPLIED_AT)) -ge 15 ] || return 0
  [ -r "$LEARN" ] || return 0
  [ "$(kv PACKAGE "$LEARN")" = "$APPLIED_PACKAGE" ] || return 0
  _fps="$(kv FPS_EST "$SNAP")"; _jank="$(kv JANK_PCT "$SNAP")"; _p95="$(kv P95_MS "$SNAP")"; _power="$(kv POWER_MW "$SNAP")"
  _bfps="$(kv FPS_P50 "$LEARN")"; _bjank="$(kv JANK_P95 "$LEARN")"; _bp95="$(kv FRAME_P95_P95_MS "$LEARN")"; _bpower="$(kv POWER_P95_MW "$LEARN")"
  _bad=0
  awk -v f="$_fps" -v bf="$_bfps" -v j="$_jank" -v bj="$_bjank" -v p="$_p95" -v bp="$_bp95" -v w="$_power" -v bw="$_bpower" 'BEGIN{
    if(f!~/^[0-9]+([.][0-9]+)?$/ || p!~/^[0-9]+([.][0-9]+)?$/ || bf<=0 || bp<=0) exit 2;
    bad=(f<bf*0.92 || p>bp*1.20);
    if(j~/^[0-9]+([.][0-9]+)?$/ && bj>0 && j>bj*1.35+1) bad=1;
    if(w~/^[0-9]+([.][0-9]+)?$/ && bw>0 && w>bw*1.20) bad=1;
    exit bad?1:0
  }'
  _rc=$?
  [ "$_rc" -eq 2 ] && return 0
  MONITOR_SAMPLES=$((MONITOR_SAMPLES+1))
  if [ "$_rc" -eq 1 ]; then MONITOR_BAD_COUNT=$((MONITOR_BAD_COUNT+1)); else MONITOR_BAD_COUNT=0; fi
  {
    echo "DIGEST=$ACTIVE_DIGEST"
    echo "BAD_COUNT=$MONITOR_BAD_COUNT"
    echo "SAMPLES=$MONITOR_SAMPLES"
    echo "UPDATED_AT=$_now"
  } > "$MONITOR.tmp.$"; chmod 600 "$MONITOR.tmp.$"; mv -f "$MONITOR.tmp.$" "$MONITOR"
  [ "$MONITOR_BAD_COUNT" -lt 3 ] || return 1
  return 0
}

reconcile(){
  load_active
  if gate; then
    if [ "$ACTIVE_DIGEST" = "$GATE_DIGEST" ] && [ -r "$BACKUP" ]; then
      if ! active_readback_ok; then
        READBACK=DRIFT; restore_all || true; publish ROLLED_BACK SYSFS_DRIFT; return 1
      fi
      if ! post_apply_monitor; then
        READBACK=VERIFIED; restore_all || true; publish ROLLED_BACK POST_APPLY_REGRESSION; return 1
      fi
      READBACK=VERIFIED; publish APPLIED ACTIVE_APPROVAL; return 0
    fi
    [ "$ACTIVE_DIGEST" = NONE ] || restore_all
    if apply_all; then publish APPLIED CONSENSUS_SHADOW_APPROVED; return 0; fi
    restore_all || true; READBACK=FAILED; publish ROLLED_BACK APPLY_OR_READBACK_FAILED; return 1
  fi
  if [ "$ACTIVE_DIGEST" != NONE ] || [ -r "$BACKUP" ]; then
    restore_all || true; publish ROLLED_BACK "$GATE_REASON"
  else
    ACTIVE_DIGEST=NONE; APPLIED_PACKAGE=NONE; APPLIED_LITTLE=NA; APPLIED_BIG=NA; APPLIED_GPU=NA; READBACK=NA; ROLLBACK_STATE=STANDBY
    publish IDLE "$GATE_REASON"
  fi
}

case "$MODE" in
  once) reconcile ;;
  daemon)
    trap 'restore_all >/dev/null 2>&1 || true; exit 0' INT TERM EXIT
    while :; do reconcile >/dev/null 2>&1 || true; sleep 2; done
    ;;
  *) echo "usage: executor.sh ROOT {once|daemon}"; exit 2 ;;
esac
