#!/system/bin/sh
ROOT="$1"
POLICY="$ROOT/policy/candidate.env"
STATE="$ROOT/runtime/executor.env"
SNAP="$ROOT/runtime/snapshot.env"
LEARN="$ROOT/history/learned_envelope.env"
ROLLBACK="$ROOT/policy/rollback.env"
LAST_HASH=""

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }

write_state() {
  tmp="$STATE.tmp.$$"
  {
    echo "EXECUTOR_STATE=$1"
    echo "EXECUTOR_DETAIL=$2"
    echo "UPDATED_AT=$(date +%s)"
  } > "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$STATE"
}

allowed_node() {
  case "$1" in
    /sys/devices/system/cpu/cpufreq/policy[0-9]*/scaling_max_freq|    /sys/devices/system/cpu/cpufreq/policy[0-9]*/scaling_min_freq|    /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_max_freq|    /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_min_freq|    /sys/class/kgsl/kgsl-3d0/devfreq/max_freq|    /sys/class/kgsl/kgsl-3d0/devfreq/min_freq|    /sys/class/devfreq/*gpu*/max_freq|    /sys/class/devfreq/*gpu*/min_freq|    /sys/class/devfreq/*mali*/max_freq|    /sys/class/devfreq/*mali*/min_freq) return 0 ;;
    *) return 1 ;;
  esac
}

value_allowed() {
  node="$1"
  value="$2"
  case "$value" in ''|*[!0-9]*) return 1;; esac
  [ "$value" -gt 0 ] || return 1

  base=$(dirname "$node")
  case "$node" in
    */cpufreq/*|/sys/devices/system/cpu/cpufreq/policy*/*)
      af="$base/scaling_available_frequencies"
      if [ -r "$af" ]; then
        for x in $(cat "$af" 2>/dev/null); do
          [ "$x" = "$value" ] && return 0
        done
        return 1
      fi
      lo=$(cat "$base/cpuinfo_min_freq" 2>/dev/null)
      hi=$(cat "$base/cpuinfo_max_freq" 2>/dev/null)
      case "$lo:$hi" in *[!0-9:]*|:*) return 1;; esac
      [ "$value" -ge "$lo" ] && [ "$value" -le "$hi" ]
      return
      ;;
    *)
      af="$base/available_frequencies"
      [ -r "$af" ] || return 1
      for x in $(cat "$af" 2>/dev/null); do
        [ "$x" = "$value" ] && return 0
      done
      return 1
      ;;
  esac
}

rollback_all() {
  [ -r "$ROLLBACK" ] || return
  while IFS='|' read -r node old; do
    allowed_node "$node" || continue
    [ -w "$node" ] || continue
    echo "$old" > "$node" 2>/dev/null
  done < "$ROLLBACK"
}

write_state OBSERVE_ONLY "waiting for mature stock baseline + AI consensus + shadow pass"

while true; do
  [ -r "$POLICY" ] || { sleep 5; continue; }
  [ -r "$SNAP" ] || { write_state OBSERVE_ONLY "observer snapshot unavailable"; sleep 5; continue; }
  [ -r "$LEARN" ] || { write_state OBSERVE_ONLY "learner baseline unavailable"; sleep 5; continue; }

  [ "$(kv STATE "$LEARN")" = READY_HARDWARE_MODEL ] || { write_state OBSERVE_ONLY "stock baseline not mature"; sleep 5; continue; }
  [ "$(kv FRAME_EVIDENCE "$LEARN")" = VALID ] || { write_state OBSERVE_ONLY "frame baseline not mature"; sleep 5; continue; }

  POLICY_PKG=$(kv PACKAGE "$POLICY")
  [ -n "$POLICY_PKG" ] && [ "$POLICY_PKG" = "$(kv PACKAGE "$LEARN")" ] && [ "$POLICY_PKG" = "$(kv ACTIVE_PACKAGE "$SNAP")" ] || {
    write_state OBSERVE_ONLY "policy context mismatch"; sleep 5; continue;
  }

  VERDICT=$(kv VERDICT "$POLICY")
  CONF=$(kv CONFIDENCE "$POLICY")
  SHADOW=$(kv SHADOW_PASS "$POLICY")
  EXEC=$(kv EXECUTOR_ENABLED "$POLICY")

  [ "$VERDICT" = APPROVED ] || { write_state OBSERVE_ONLY "policy not approved"; sleep 5; continue; }
  [ "$SHADOW" = YES ] || { write_state OBSERVE_ONLY "shadow comparison not passed"; sleep 5; continue; }
  [ "$EXEC" = 1 ] || { write_state OBSERVE_ONLY "executor gate disabled"; sleep 5; continue; }
  case "$CONF" in ''|*[!0-9]*) write_state REJECTED "invalid confidence"; sleep 5; continue;; esac
  [ "$CONF" -ge 90 ] || { write_state REJECTED "confidence below 90"; sleep 5; continue; }

  HASH=$(sha256sum "$POLICY" 2>/dev/null | awk '{print $1}')
  [ -n "$HASH" ] && [ "$HASH" = "$LAST_HASH" ] && { sleep 5; continue; }

  FAIL=0
  : > "$ROLLBACK"
  chmod 600 "$ROLLBACK"

  while IFS='|' read -r tag node value; do
    [ "$tag" = SYSFS ] || continue
    allowed_node "$node" || { FAIL=1; break; }
    [ -w "$node" ] || { FAIL=1; break; }
    value_allowed "$node" "$value" || { FAIL=1; break; }
    old=$(cat "$node" 2>/dev/null)
    case "$old" in ''|*[!0-9]*) FAIL=1; break;; esac
    echo "$node|$old" >> "$ROLLBACK"
  done < "$POLICY"

  if [ "$FAIL" -ne 0 ]; then
    write_state REJECTED "allowlist/frequency validation failed"
    sleep 5
    continue
  fi

  while IFS='|' read -r tag node value; do
    [ "$tag" = SYSFS ] || continue
    echo "$value" > "$node" 2>/dev/null || { FAIL=1; break; }
    check=$(cat "$node" 2>/dev/null)
    [ "$check" = "$value" ] || { FAIL=1; break; }
  done < "$POLICY"

  if [ "$FAIL" -eq 0 ]; then
    LAST_HASH="$HASH"
    write_state APPLIED "validated adaptive policy"
  else
    rollback_all
    write_state ROLLED_BACK "write/verification failure; previous sysfs values restored"
  fi
  sleep 5
done
