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
  valid_cpu "$LP" && pair_restore "$LP" scaling_min_freq scaling_max_freq "$(kv LITTLE_MIN "$BACKUP")" "$(kv LITTLE_MAX "$BACKUP")" || true
  valid_cpu "$BP" && pair_restore "$BP" scaling_min_freq scaling_max_freq "$(kv BIG_MIN "$BACKUP")" "$(kv BIG_MAX "$BACKUP")" || true
  valid_gpu "$GP" && pair_restore "$GP" min_freq max_freq "$(kv GPU_MIN "$BACKUP")" "$(kv GPU_MAX "$BACKUP")" || true
  rm -f "$BACKUP"
  ACTIVE_DIGEST=NONE; APPLIED_PACKAGE=NONE; APPLIED_LITTLE=NA; APPLIED_BIG=NA; APPLIED_GPU=NA
  ROLLBACK_STATE=RESTORED
}

snapshot_fresh(){
  _e="$(kv EPOCH "$SNAP")"; num "$_e" || return 1
  _age=$(( $(date +%s) - _e ))
  [ "$_age" -ge 0 ] && [ "$_age" -le 12 ]
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
  _exp="$(kv EXPIRES_AT "$APPROVAL")"; num "$_exp" && [ "$_exp" -ge "$(date +%s)" ] || { GATE_REASON=APPROVAL_EXPIRED; return 1; }
  [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" = GAME ] || { GATE_REASON=NON_GAME; return 1; }
  [ "$(kv PACKAGE "$WORKLOAD")" = "$(kv PACKAGE "$POLICY")" ] && [ "$(kv ACTIVE_PACKAGE "$SNAP")" = "$(kv PACKAGE "$POLICY")" ] || { GATE_REASON=PACKAGE_MISMATCH; return 1; }
  snapshot_fresh || { GATE_REASON=STALE_SNAPSHOT; return 1; }
  thermal_safe || { GATE_REASON=THERMAL_GUARD; return 1; }

  LP="$(kv LITTLE_POLICY_PATH "$SNAP")"; BP="$(kv BIG_POLICY_PATH "$SNAP")"; GP="$(kv GPU_DEVFREQ_PATH "$SNAP")"
  valid_cpu "$LP" && valid_cpu "$BP" && valid_gpu "$GP" || { GATE_REASON=PATH_REJECTED; return 1; }

  LMIN="$(kv LITTLE_MIN_KHZ "$POLICY")"; LMAX="$(kv LITTLE_MAX_KHZ "$POLICY")"
  BMIN="$(kv BIG_MIN_KHZ "$POLICY")"; BMAX="$(kv BIG_MAX_KHZ "$POLICY")"
  GMIN="$(kv GPU_MIN_HZ "$POLICY")"; GMAX="$(kv GPU_MAX_HZ "$POLICY")"
  for _v in "$LMIN" "$LMAX" "$BMIN" "$BMAX" "$GMIN" "$GMAX"; do num "$_v" || { GATE_REASON=NON_NUMERIC; return 1; }; done
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
}

reconcile(){
  load_active
  if gate; then
    if [ "$ACTIVE_DIGEST" = "$GATE_DIGEST" ] && [ -r "$BACKUP" ]; then
      READBACK=VERIFIED; publish APPLIED ACTIVE_APPROVAL; return 0
    fi
    [ "$ACTIVE_DIGEST" = NONE ] || restore_all
    if apply_all; then publish APPLIED CONSENSUS_SHADOW_APPROVED; return 0; fi
    restore_all; READBACK=FAILED; publish ROLLED_BACK APPLY_OR_READBACK_FAILED; return 1
  fi
  if [ "$ACTIVE_DIGEST" != NONE ] || [ -r "$BACKUP" ]; then
    restore_all; publish ROLLED_BACK "$GATE_REASON"
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
