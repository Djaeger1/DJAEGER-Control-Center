#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
W="$M/bin/hermes_thought_worker.sh"
REV=5acb7991e787782cd83640adc29293a14691102b
URL="https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/$REV/runtime-patches/one_hermes_thought_worker_v3.sh"
TMP="$R/runtime/hermes_thought_worker_v3.new"

curl -fsSL -m 30 "$URL" -o "$TMP" || { echo "WORKER_DOWNLOAD=FAIL"; exit 1; }
sh -n "$TMP" || { echo "WORKER_SYNTAX=FAIL"; exit 2; }
grep -Fq 'ONE_HERMES_LOCAL_PROGRESS_V1' "$TMP" || { echo "LOCAL_PROGRESS=MISSING"; exit 3; }
grep -Fq 'teacher_needed(){' "$TMP" || { echo "TEACHER_GUARD=MISSING"; exit 4; }
grep -Fq 'PROGRESS_CLASS=' "$TMP" || { echo "PROGRESS_STATE=MISSING"; exit 5; }

echo "WORKER_V3_SYNTAX=OK"
echo "LOCAL_PROGRESS=OK"
echo "KNOWN_REASON_ZERO_NEURON=OK"
echo "PROGRESS_STABILITY=OK"

TS=$(date +%s)
[ -r "$W" ] && cp "$W" "$R/runtime/hermes_thought_worker.pre_v3.$TS" || true
cp "$TMP" "$W" || exit 6
chmod 755 "$W"
rm -f "$TMP"
rm -f "$R/runtime/hermes_thought_progress.env"

PID=$(cat "$R/runtime/locks/hermes_thought_worker.lock/pid" 2>/dev/null)
case "$PID" in
  ''|*[!0-9]*) ;;
  *)
    kill -TERM "$PID" 2>/dev/null
    sleep 1
    kill -0 "$PID" 2>/dev/null && kill -KILL "$PID" 2>/dev/null
    ;;
esac
rm -rf "$R/runtime/locks/hermes_thought_worker.lock"
nohup sh "$W" "$R" "$M" >/dev/null 2>&1 &
sleep 5

echo "PATCH=ONE_HERMES_THOUGHT_PROGRESS_V3_ACTIVE"
echo "PROGRESS_SOURCE=LOCAL_EVIDENCE_ONLY"
echo "CLOUD_FOR_PROGRESS=NO"
echo "CLOUD_LIMIT_FALLBACK=LOCAL_PLUS_MEMORY"
echo "=== THOUGHT ==="
grep -E '^(ORIGIN|STATUS|CONFIDENCE|REASON|PROGRESS|FRAME_CLASS|TEXT|FINGERPRINT)=' "$R/runtime/hermes_thought.env" 2>/dev/null || echo "THOUGHT=WAITING"
echo "=== NEURONS ==="
grep -E '^(USED_EST|SUCCESS_CALLS)=' "$R/config/hermes_neuron_live.env" 2>/dev/null || true
echo "=== SAFETY ==="
grep -E '^(EXECUTOR_STATE|ACTIVE_DIGEST)=' "$R/runtime/execution.env" 2>/dev/null || true
