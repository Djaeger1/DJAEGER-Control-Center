#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
W="$M/bin/hermes_thought_worker.sh"
REV=4bd61b5ef6c1b9297439c20f2ab8fbced4474fc5
URL="https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/$REV/runtime-patches/one_hermes_thought_worker_v2.sh"
TMP="$R/runtime/hermes_thought_worker_v2.new"

curl -fsSL -m 30 "$URL" -o "$TMP" || { echo "WORKER_DOWNLOAD=FAIL"; exit 1; }
sh -n "$TMP" || { echo "WORKER_SYNTAX=FAIL"; exit 2; }
grep -Fq 'teacher_needed(){' "$TMP" || { echo "TEACHER_GUARD=MISSING"; exit 3; }
grep -Fq 'Known semantic classes are already understood by Local and must cost 0 neurons.' "$TMP" || { echo "KNOWN_REASON_GUARD=MISSING"; exit 4; }
grep -Fq '"content"' "$TMP" || { echo "PARSER_FALLBACK=MISSING"; exit 5; }

echo "WORKER_V2_SYNTAX=OK"
echo "KNOWN_REASON_ZERO_NEURON=OK"
echo "CLOUD_RESPONSE_FALLBACK=OK"

TS=$(date +%s)
[ -r "$W" ] && cp "$W" "$R/runtime/hermes_thought_worker.pre_v2.$TS" || true
cp "$TMP" "$W" || exit 6
chmod 755 "$W"
rm -f "$TMP"

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
sleep 4

echo "PATCH=ONE_HERMES_THOUGHT_LEARNING_V2_ACTIVE"
echo "TEACHER_POLICY=UNKNOWN_REASON_ONLY"
echo "KNOWN_LOCAL_REASON=ZERO_NEURON"
echo "CLOUD_LIMIT_FALLBACK=LOCAL_PLUS_MEMORY"
echo "=== THOUGHT ==="
grep -E '^(ORIGIN|STATUS|CONFIDENCE|REASON|TEXT|FINGERPRINT)=' "$R/runtime/hermes_thought.env" 2>/dev/null || echo "THOUGHT=WAITING"
echo "=== KNOWLEDGE ==="
K="$R/history/hermes_thought_knowledge.tsv"
if [ -r "$K" ]; then
  N=$(wc -l < "$K" 2>/dev/null); case "$N" in ''|*[!0-9]*) N=0;; esac
  [ "$N" -gt 0 ] && N=$((N-1))
  echo "KNOWLEDGE_ROWS=$N"
else
  echo "KNOWLEDGE_ROWS=0"
fi
echo "=== TEACHER_GUARD ==="
grep -E '^(LAST_SUCCESS_AT|BLOCK_UNTIL|LAST_HTTP)=' "$R/config/hermes_thought_teacher_guard.env" 2>/dev/null || true
echo "=== NEURONS ==="
grep -E '^(USED_EST|SUCCESS_CALLS)=' "$R/config/hermes_neuron_live.env" 2>/dev/null || true
echo "=== SAFETY ==="
grep -E '^(EXECUTOR_STATE|ACTIVE_DIGEST)=' "$R/runtime/execution.env" 2>/dev/null || true
