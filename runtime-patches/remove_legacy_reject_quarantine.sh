#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
W="$R/runtime/remove_legacy_reject_quarantine"
N="$W/hermes.new"
mkdir -p "$W" || exit 1

# Remove only the obsolete transient digest-based quarantine block.
# The newer semantic multi-reject matcher/ledger remains authoritative.
awk '
  BEGIN{skip=0; removed=0}
  {
    if ($0 ~ /^  # SHADOW_REJECT_QUARANTINE:/) {
      skip=1
      removed=1
      next
    }
    if (skip && $0 ~ /^  # Above the hard thermal ceiling/) {
      skip=0
      print
      next
    }
    if (skip) next
    print
  }
  END{if(!removed) exit 42}
' "$H" > "$N" || exit 42

sh -n "$N" || exit 51
grep -Fq "MULTI_REJECT_ALTERNATIVE_SYNTH" "$N" || exit 52
grep -Fq "strategy_quarantined_file(){" "$N" || exit 53
grep -Fq "HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD" "$N" || exit 54
grep -Fq "REJECT_QUARANTINE_OBSERVE_BARRIER" "$N" || exit 55
if grep -Fq "SHADOW_REJECT_QUARANTINE:" "$N"; then exit 56; fi

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_remove_legacy_quarantine.$TS" || exit 61
cp "$N" "$H" || exit 62
chmod 755 "$H"

P=$(cat "$R/runtime/locks/hermes_adapter.lock/pid" 2>/dev/null)
case "$P" in
  ""|*[!0-9]*) ;;
  *)
    kill -TERM "$P" 2>/dev/null
    sleep 1
    kill -0 "$P" 2>/dev/null && kill -KILL "$P" 2>/dev/null
    ;;
esac
rm -rf "$R/runtime/locks/hermes_adapter.lock"
nohup sh "$H" "$R" "$M" >/dev/null 2>&1 &

echo "PATCH=LEGACY_REJECT_QUARANTINE_REMOVED"
echo "HERMES_SYNTAX=OK"
