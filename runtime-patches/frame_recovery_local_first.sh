#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
W="$R/runtime/frame_recovery_local_first"
N="$W/hermes.new"
SN="$W/local_first.snip"
mkdir -p "$W" || exit 1

cat > "$SN" <<'EOF'
  # FRAME_RECOVERY_LOCAL_BEFORE_CLOUD
  # Frame stability is the first human-comfort objective. When the device is
  # already below the hard thermal gate, try deterministic local synthesis
  # before spending a Cloud neuron. Shadow remains mandatory before executor.
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
  cp "$H" "$N"
else
  COUNT=$(grep -c '^  # Gemini unavailable outside the local comfort path:' "$H" 2>/dev/null || true)
  echo "INSERT_ANCHORS=$COUNT"
  [ "$COUNT" = 1 ] || exit 41

  awk -v SNIP="$SN" '
    BEGIN{done=0}
    {
      if($0=="  # Gemini unavailable outside the local comfort path:" && !done){
        while((getline x < SNIP)>0) print x
        close(SNIP)
        done=1
      }
      print
    }
    END{if(!done) exit 42}
  ' "$H" > "$N" || exit 42
fi

sh -n "$N" || exit 51
grep -Fq "FRAME_RECOVERY_LOCAL_BEFORE_CLOUD" "$N" || exit 52
grep -Fq "HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD" "$N" || exit 53
grep -Fq "MULTI_REJECT_ALTERNATIVE_SYNTH" "$N" || exit 54
grep -Fq "REJECT_QUARANTINE_NO_CLOUD" "$N" || exit 55

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_frame_recovery_local_first.$TS" || exit 61
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

echo "PATCH=FRAME_RECOVERY_LOCAL_FIRST_ACTIVE"
echo "HERMES_SYNTAX=OK"
