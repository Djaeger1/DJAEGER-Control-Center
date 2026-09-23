#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
W="$M/bin/hermes_thought_worker.sh"
REV=ad93898fa435db8d1d9a160d1383997eb4640b5b
URL="https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/$REV/runtime-patches/one_hermes_thought_worker_v3_2.sh"
TMP="$R/runtime/hermes_thought_worker_v3_2.new"
STATE="$R/runtime/hermes_thought_worker_state.env"
OUT="$R/runtime/hermes_thought.env"

curl -fsSL -m 30 "$URL" -o "$TMP" || { echo "WORKER_DOWNLOAD=FAIL"; exit 1; }
sh -n "$TMP" || { echo "WORKER_SYNTAX=FAIL"; exit 2; }
grep -Fq "WORKER_VERSION=ONE_HERMES_THOUGHT_V3_2" "$TMP" || { echo "WORKER_ID=MISSING"; exit 3; }
grep -Fq "ONE_HERMES_LOCAL_PROGRESS_V1" "$TMP" || { echo "LOCAL_PROGRESS=MISSING"; exit 4; }
grep -Fq 'echo "PID=$$"' "$TMP" || { echo "PID_FIX=MISSING"; exit 5; }
grep -Fq 'echo "WORKER_PID=$$"' "$TMP" || { echo "THOUGHT_PID_FIX=MISSING"; exit 6; }

echo "WORKER_V3_2_SYNTAX=OK"
echo "PID_FIX=OK"
echo "LOCAL_PROGRESS=OK"

TS=$(date +%s)
[ -r "$W" ] && cp "$W" "$R/runtime/hermes_thought_worker.pre_v3_2.$TS" || true
cp "$TMP" "$W" || exit 7
chmod 755 "$W"
rm -f "$TMP"

OLD=$(cat "$R/runtime/locks/hermes_thought_worker.lock/pid" 2>/dev/null)
case "$OLD" in
  ""|*[!0-9]*) ;;
  *)
    kill -TERM "$OLD" 2>/dev/null || true
    I=0
    while kill -0 "$OLD" 2>/dev/null && [ "$I" -lt 3 ]; do sleep 1; I=$((I+1)); done
    kill -0 "$OLD" 2>/dev/null && kill -KILL "$OLD" 2>/dev/null || true
    ;;
esac
rm -rf "$R/runtime/locks/hermes_thought_worker.lock"
rm -f "$STATE" "$R/runtime/hermes_thought_progress.env"

nohup sh "$W" "$R" "$M" >/dev/null 2>&1 &

# Runtime verification: worker state AND published thought must both be V3.2.
I=0
while [ "$I" -lt 25 ]; do
  SV=$(sed -n "s/^WORKER_VERSION=//p" "$STATE" 2>/dev/null | head -n1)
  TV=$(sed -n "s/^WORKER_VERSION=//p" "$OUT" 2>/dev/null | head -n1)
  PG=$(sed -n "s/^PROGRESS=//p" "$OUT" 2>/dev/null | head -n1)
  FC=$(sed -n "s/^FRAME_CLASS=//p" "$OUT" 2>/dev/null | head -n1)
  [ "$SV" = ONE_HERMES_THOUGHT_V3_2 ] && [ "$TV" = ONE_HERMES_THOUGHT_V3_2 ] && [ -n "$PG" ] && [ -n "$FC" ] && break
  sleep 1
  I=$((I+1))
done

SV=$(sed -n "s/^WORKER_VERSION=//p" "$STATE" 2>/dev/null | head -n1)
SP=$(sed -n "s/^PID=//p" "$STATE" 2>/dev/null | head -n1)
HB=$(sed -n "s/^HEARTBEAT_AT=//p" "$STATE" 2>/dev/null | head -n1)
TV=$(sed -n "s/^WORKER_VERSION=//p" "$OUT" 2>/dev/null | head -n1)

echo "PATCH=ONE_HERMES_THOUGHT_V3_2_ACTIVE"
echo "STATE_WORKER_VERSION=${SV:-MISSING}"
echo "STATE_WORKER_PID=${SP:-MISSING}"
echo "HEARTBEAT_AT=${HB:-MISSING}"
echo "THOUGHT_WORKER_VERSION=${TV:-MISSING}"

if [ "$SV" != ONE_HERMES_THOUGHT_V3_2 ] || [ "$TV" != ONE_HERMES_THOUGHT_V3_2 ]; then
  echo "RUNTIME_VERIFY=FAIL"
  exit 8
fi

echo "RUNTIME_VERIFY=OK"
echo "=== THOUGHT ==="
grep -E "^(WORKER_VERSION|WORKER_PID|FINGERPRINT|ORIGIN|STATUS|CONFIDENCE|REASON|PROGRESS|FRAME_CLASS|EVIDENCE|TEXT)=" "$OUT" 2>/dev/null
echo "=== NEURONS ==="
grep -E "^(USED_EST|SUCCESS_CALLS)=" "$R/config/hermes_neuron_live.env" 2>/dev/null || true
echo "=== SAFETY ==="
grep -E "^(EXECUTOR_STATE|ACTIVE_DIGEST)=" "$R/runtime/execution.env" 2>/dev/null || true
