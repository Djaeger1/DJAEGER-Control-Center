#!/system/bin/sh
ROOT="$1"
POLICY="$ROOT/policy/candidate.env"
STATE="$ROOT/runtime/executor.env"
SNAP="$ROOT/runtime/snapshot.env"
ROLLBACK="$ROOT/policy/rollback.env"
LAST_HASH=""

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
    /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_max_freq|/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_min_freq|/sys/class/kgsl/kgsl-3d0/devfreq/max_freq|/sys/class/kgsl/kgsl-3d0/devfreq/min_freq|/sys/class/devfreq/*gpu*/max_freq|/sys/class/devfreq/*gpu*/min_freq|/sys/class/devfreq/*mali*/max_freq|/sys/class/devfreq/*mali*/min_freq) return 0 ;;
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
    /sys/devices/system/cpu/*/cpufreq/*)
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

  LEARN=$(grep '^LEARNING_STATE=' "$SNAP" | cut -d= -f2-)
  [ "$LEARN" = "BASELINE_MATURE" ] || { write_state OBSERVE_ONLY "stock baseline not mature"; sleep 5; continue; }

  VERDICT=$(grep '^VERDICT=' "$POLICY" | cut -d= -f2-)
  CONF=$(grep '^CONFIDENCE=' "$POLICY" | cut -d= -f2-)
  SHADOW=$(grep '^SHADOW_PASS=' "$POLICY" | cut -d= -f2-)
  EXEC=$(grep '^EXECUTOR_ENABLED=' "$POLICY" | cut -d= -f2-)

  [ "$VERDICT" = "APPROVED" ] || { write_state OBSERVE_ONLY "policy not approved"; sleep 5; continue; }
  [ "$SHADOW" = "YES" ] || { write_state OBSERVE_ONLY "shadow comparison not passed"; sleep 5; continue; }
  [ "$EXEC" = "1" ] || { write_state OBSERVE_ONLY "executor gate disabled"; sleep 5; continue; }
  case "$CONF" in ''|*[!0-9]*) write_state REJECTED "invalid confidence"; sleep 5; continue;; esac
  [ "$CONF" -ge 90 ] || { write_state REJECTED "confidence below 90"; sleep 5; continue; }

  HASH=$(sha256sum "$POLICY" 2>/dev/null | awk '{print $1}')
  [ -n "$HASH" ] && [ "$HASH" = "$LAST_HASH" ] && { sleep 5; continue; }

  FAIL=0
  : > "$ROLLBACK"
  chmod 600 "$ROLLBACK"

  while IFS='|' read -r tag node value; do
    [ "$tag" = "SYSFS" ] || continue
    allowed_node "$node" || { FAIL=1; break; }
    [ -w "$node" ] || { FAIL=1; break; }
    value_allowed "$node" "$value" || { FAIL=1; break; }
    old=$(cat "$node" 2>/dev/null)
    case "$old" in ''|*[!0-9]*) FAIL=1; break;; esac
    echo "$node|$old" >> "$ROLLBACK"
  done < "$POLICY"

  if [ "$FAIL" -ne 0 ]; then
    write_state REJECTED "allowlist/range validation failed"
    sleep 5
    continue
  fi

  while IFS='|' read -r tag node value; do
    [ "$tag" = "SYSFS" ] || continue
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
