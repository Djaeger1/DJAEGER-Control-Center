#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
W="$R/runtime/remove_legacy_reject_quarantine_v2"
N="$W/hermes.new"
mkdir -p "$W" || exit 1

START_COUNT=$(grep -c '^  # SHADOW_REJECT_QUARANTINE:' "$H" 2>/dev/null || true)
END_COUNT=$(grep -c '^  # With healthy frame pacing but user discomfort from heat' "$H" 2>/dev/null || true)

echo "LEGACY_START_MARKERS=$START_COUNT"
echo "COMFORT_END_MARKERS=$END_COUNT"

[ "$START_COUNT" = 1 ] || exit 41
[ "$END_COUNT" = 1 ] || exit 42

awk '
  BEGIN{skip=0; removed=0; resumed=0}
  {
    if (!skip && $0 ~ /^  # SHADOW_REJECT_QUARANTINE:/) {
      skip=1
      removed++
      next
    }
    if (skip && $0 ~ /^  # With healthy frame pacing but user discomfort from heat/) {
      skip=0
      resumed++
      print
      next
    }
    if (skip) next
    print
  }
  END{
    if(skip || removed!=1 || resumed!=1) exit 43
  }
' "$H" > "$N" || exit 43

sh -n "$N" || exit 51

grep -Fq "MULTI_REJECT_ALTERNATIVE_SYNTH" "$N" || exit 52
grep -Fq "strategy_quarantined_file(){" "$N" || exit 53
grep -Fq "HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD" "$N" || exit 54
grep -Fq "REJECT_QUARANTINE_OBSERVE_BARRIER" "$N" || exit 55
grep -Fq "PERSISTENT_SHADOW_REJECT_QUARANTINE" "$N" && exit 56
grep -Fq "SHADOW_REJECT_QUARANTINE:" "$N" && exit 57

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_remove_legacy_quarantine_v2.$TS" || exit 61
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

echo "PATCH=LEGACY_REJECT_QUARANTINE_V2_REMOVED"
echo "HERMES_SYNTAX=OK"
