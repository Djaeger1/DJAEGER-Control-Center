#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
W="$R/runtime/frame_recovery_local_first_v3"
N="$W/hermes.new"
SN="$W/local_first.snip"
mkdir -p "$W" || exit 1

cat > "$SN" <<'EOF'
  # FRAME_RECOVERY_LOCAL_BEFORE_CLOUD
  # Frame stability first. Below the hard thermal gate, deterministic local
  # synthesis gets first chance; Cloud is fallback only. Shadow still gates
  # executor authority.
  if frame_degraded; then
    if local_synthesize_takeover; then
      HLOCAL_STATE=TAKEOVER_LOCAL_SYNTH
      HACTIVE_SOURCE=HERMES_LOCAL
      HCLOUD_STATE=REACHABLE_IDLE
      HCLOUD_USED=NO
      write_state HERMES_TAKEOVER
      sleep 10
      continue
    fi
  fi

EOF

if grep -Fq "FRAME_RECOVERY_LOCAL_BEFORE_CLOUD" "$H"; then
  cp "$H" "$N" || exit 40
  echo "INSERT=ALREADY_PRESENT"
else
  COUNT=$(grep -c 'Gemini unavailable outside the local comfort path:' "$H" 2>/dev/null || true)
  echo "INSERT_ANCHORS=$COUNT"
  [ "$COUNT" = 1 ] || exit 41

  awk -v SNIP="$SN" '
    BEGIN{done=0}
    {
      if(!done && index($0,"Gemini unavailable outside the local comfort path:")>0){
        while((getline x < SNIP)>0) print x
        close(SNIP)
        done=1
      }
      print
    }
    END{
      if(done!=1) exit 42
    }
  ' "$H" > "$N" || { echo "INSERT=FAIL"; exit 42; }

  echo "INSERT=OK"
fi

if sh -n "$N"; then
  echo "HERMES_CANDIDATE_SYNTAX=OK"
else
  echo "HERMES_CANDIDATE_SYNTAX=FAIL"
  exit 51
fi

for MARK in   FRAME_RECOVERY_LOCAL_BEFORE_CLOUD   MULTI_REJECT_ALTERNATIVE_SYNTH   REJECT_QUARANTINE_NO_CLOUD
do
  if grep -Fq "$MARK" "$N"; then
    echo "$MARK=OK"
  else
    echo "$MARK=MISSING"
    exit 52
  fi
done

if grep -Fq "HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD" "$N"; then
  echo "HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD=OK"
else
  echo "HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD=MISSING"
fi

HARD_LINE=$(grep -n 'if hard_thermal_guard_active; then' "$N" | head -n1 | cut -d: -f1)
LOCAL_LINE=$(grep -n '# FRAME_RECOVERY_LOCAL_BEFORE_CLOUD' "$N" | head -n1 | cut -d: -f1)
CLOUD_LINE=$(awk -v local="$LOCAL_LINE" '
  NR>local && $0 ~ /^  if cloud_takeover; then/ {print NR; exit}
' "$N")

case "$HARD_LINE:$LOCAL_LINE:$CLOUD_LINE" in
  *[!0-9:]*|:*|*:) echo "ORDER_MARKERS=INVALID"; exit 53;;
esac

echo "HARD_LINE=$HARD_LINE"
echo "LOCAL_FRAME_LINE=$LOCAL_LINE"
echo "NEXT_CLOUD_LINE=$CLOUD_LINE"

[ "$HARD_LINE" -lt "$LOCAL_LINE" ] || {
  echo "ORDER=FAIL_HARD_BEFORE_LOCAL"
  exit 54
}
[ "$LOCAL_LINE" -lt "$CLOUD_LINE" ] || {
  echo "ORDER=FAIL_LOCAL_BEFORE_CLOUD"
  exit 55
}

echo "ORDER=HARD_THERMAL_THEN_LOCAL_FRAME_THEN_CLOUD"

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_frame_recovery_local_first_v3.$TS" || exit 61
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

echo "PATCH=FRAME_RECOVERY_LOCAL_FIRST_V3_ACTIVE"
echo "HERMES_SYNTAX=OK"
