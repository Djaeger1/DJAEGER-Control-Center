#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
W="$R/runtime/healthy_local_observe_patch"
N="$W/hermes.new"
SN="$W/observe.snip"
mkdir -p "$W" || exit 1

cat > "$SN" <<'EOF'
  # HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD
  # Do not spend Cloud neurons just because Gemini is unavailable.
  # If frame pacing, thermal comfort and power are all currently acceptable,
  # the correct decision is local observe.
  if ! frame_degraded && ! thermal_pressure && ! power_pressure; then
    rm -f "$HPLAN" "$LOCAL_OUT"
    HLOCAL_STATE=TAKEOVER_OBSERVE
    HACTIVE_SOURCE=HERMES_LOCAL
    HCLOUD_STATE=REACHABLE_IDLE
    HDETAIL=healthy_local_observe_no_cloud_needed
    write_state HERMES_TAKEOVER
    sleep 15
    continue
  fi

EOF

if grep -Fq "HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD" "$H"; then
  cp "$H" "$N"
else
  awk -v SNIP="$SN" '
    BEGIN{done=0}
    {
      if ($0 ~ /^  # Gemini unavailable outside the local comfort path:/ && !done) {
        while ((getline x < SNIP) > 0) print x
        close(SNIP)
        done=1
      }
      print
    }
    END{if(!done) exit 42}
  ' "$H" > "$N" || exit 42
fi

sh -n "$N" || exit 51
TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_healthy_observe.$TS" || exit 61
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

echo "PATCH=HEALTHY_LOCAL_OBSERVE_BEFORE_CLOUD_ACTIVE"
echo "HERMES_SYNTAX=OK"
