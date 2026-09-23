#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
Q="$R/history/shadow_reject_strategies.csv"
W="$R/runtime/frame_recovery_stage1_contextual"
N="$W/hermes.new"
mkdir -p "$W" || exit 1

COUNT=$(grep -c '^    if frame_critical; then$' "$H" 2>/dev/null || true)
echo "FRAME_CRITICAL_ANCHORS=$COUNT"
[ "$COUNT" = 1 ] || exit 41

if grep -Fq "LOCAL_FRAME_CRITICAL_RECOVERY_STAGE1_BIG_GPU" "$H"; then
  cp "$H" "$N" || exit 42
  echo "FRAME_STAGE1=ALREADY_PRESENT"
else
  awk '
    BEGIN{skip=0; done=0}
    {
      if(!skip && $0=="    if frame_critical; then"){
        print "    if frame_critical; then"
        print "      # FRAME_RECOVERY_CONTEXTUAL_STAGE1"
        print "      # Critical recovery starts with BIG+GPU because this is the"
        print "      # least aggressive evidence-backed recovery cohort. LITTLE"
        print "      # is reserved for later escalation after post-apply evidence."
        print "      _intent=FRAME_RECOVERY"
        print "      _reason=LOCAL_FRAME_CRITICAL_RECOVERY_STAGE1_BIG_GPU"
        print "      _actuators=BIG,GPU"
        skip=1
        done=1
        next
      }
      if(skip && $0=="    else"){
        skip=0
        print
        next
      }
      if(skip) next
      print
    }
    END{
      if(skip || done!=1) exit 43
    }
  ' "$H" > "$N" || exit 43
  echo "FRAME_STAGE1=INSERTED"
fi

if sh -n "$N"; then
  echo "HERMES_CANDIDATE_SYNTAX=OK"
else
  echo "HERMES_CANDIDATE_SYNTAX=FAIL"
  exit 51
fi

for MARK in   FRAME_RECOVERY_LOCAL_BEFORE_CLOUD   MULTI_REJECT_ALTERNATIVE_SYNTH   REJECT_QUARANTINE_NO_CLOUD   LOCAL_FRAME_CRITICAL_RECOVERY_STAGE1_BIG_GPU
do
  if grep -Fq "$MARK" "$N"; then
    echo "$MARK=OK"
  else
    echo "$MARK=MISSING"
    exit 52
  fi
done

# Contextual Shadow V2 must already be live before old reject quarantine can
# be invalidated. Old rows are archived rather than deleted.
grep -Fq "CONTEXTUAL_SHADOW_V2" "$M/bin/shadow.sh" || {
  echo "CONTEXTUAL_SHADOW_V2=MISSING"
  exit 53
}
echo "CONTEXTUAL_SHADOW_V2=OK"

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_frame_stage1.$TS" || exit 61

if [ -r "$Q" ]; then
  cp "$Q" "$R/history/shadow_reject_strategies.pre_contextual_epoch.$TS.csv" || exit 62
fi

cp "$N" "$H" || exit 63
chmod 755 "$H"

# Start a new active reject epoch under Contextual Shadow V2.
echo "AT,PACKAGE,INTENT,ACTUATORS,LITTLE_MIN_KHZ,LITTLE_MAX_KHZ,BIG_MIN_KHZ,BIG_MAX_KHZ,GPU_MIN_HZ,GPU_MAX_HZ,REASON" > "$Q.tmp.$$" || exit 64
chmod 600 "$Q.tmp.$$"
mv -f "$Q.tmp.$$" "$Q" || exit 65

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

echo "PATCH=FRAME_RECOVERY_CONTEXTUAL_STAGE1_ACTIVE"
echo "REJECT_EPOCH=CONTEXTUAL_V2_RESET"
echo "HERMES_SYNTAX=OK"
