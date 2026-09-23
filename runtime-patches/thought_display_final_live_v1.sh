#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
REV=caec5ae38ffde4a40ced6719347c2b1677ff0f82
BASE="https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/$REV/observer-next/module/bin"

G="$M/bin/gemini_reasoner.sh"
P="$M/bin/publisher.sh"
GT="$R/runtime/gemini_reasoner.final.new"
PT="$R/runtime/publisher.final.new"

curl -fsSL -m 30 "$BASE/gemini_reasoner.sh" -o "$GT" || { echo "GEMINI_DOWNLOAD=FAIL"; exit 1; }
curl -fsSL -m 30 "$BASE/publisher.sh" -o "$PT" || { echo "PUBLISHER_DOWNLOAD=FAIL"; exit 2; }

sh -n "$GT" || { echo "GEMINI_SYNTAX=FAIL"; exit 3; }
sh -n "$PT" || { echo "PUBLISHER_SYNTAX=FAIL"; exit 4; }

grep -Fq "GEMINI_THOUGHT_STATE_V1" "$GT" || { echo "GEMINI_THOUGHT_CONTRACT=MISSING"; exit 5; }
grep -Fq 'THOUGHT=$(clean_thought "$(trim "$(gv THOUGHT)")")' "$GT" || { echo "GEMINI_THOUGHT_PARSE=MISSING"; exit 6; }
grep -Fq "ONE_HERMES_THOUGHT_PUBLISHER_V1" "$PT" || { echo "HERMES_THOUGHT_DISPLAY=MISSING"; exit 7; }
grep -Fq "MAX_BYTES=104857600" "$PT" || { echo "MEMORY_100MIB=MISSING"; exit 8; }

echo "GEMINI_SYNTAX=OK"
echo "PUBLISHER_SYNTAX=OK"
echo "GEMINI_THOUGHT_CONTRACT=OK"
echo "HERMES_THOUGHT_DISPLAY=OK"
echo "MEMORY_100MIB=OK"

TS=$(date +%s)
cp "$G" "$R/runtime/gemini_reasoner.pre_thought_final.$TS" || exit 9
cp "$P" "$R/runtime/publisher.pre_thought_final.$TS" || exit 10

cp "$GT" "$G" || exit 11
cp "$PT" "$P" || exit 12
chmod 755 "$G" "$P"
rm -f "$GT" "$PT"

restart_worker(){
  _name="$1"
  _script="$2"
  _pid=$(cat "$R/runtime/locks/$_name.lock/pid" 2>/dev/null)
  case "$_pid" in
    ""|*[!0-9]*) ;;
    *)
      kill -TERM "$_pid" 2>/dev/null || true
      sleep 1
      kill -0 "$_pid" 2>/dev/null && kill -KILL "$_pid" 2>/dev/null || true
      ;;
  esac
  rm -rf "$R/runtime/locks/$_name.lock"
  nohup sh "$_script" "$R" "$M" >/dev/null 2>&1 &
}

restart_worker gemini_reasoner "$G"
restart_worker publisher_worker "$M/bin/publisher_worker.sh"

sleep 8

echo "PATCH=THOUGHT_DISPLAY_FINAL_LIVE_V1"
echo "FILES=GEMINI_REASONER+PUBLISHER"
echo "EXECUTOR_TOUCHED=NO"
echo "SHADOW_TOUCHED=NO"
echo "SYSFS_TOUCHED=NO"

echo "=== WORKERS ==="
for N in gemini_reasoner publisher_worker hermes_thought_worker shadow_contextual_v4 executor; do
  PID=$(cat "$R/runtime/locks/$N.lock/pid" 2>/dev/null)
  case "$PID" in
    ""|*[!0-9]*) echo "$N=MISSING" ;;
    *) kill -0 "$PID" 2>/dev/null && echo "$N=RUNNING:$PID" || echo "$N=DEAD:$PID" ;;
  esac
done

echo "=== GEMINI THOUGHT STATE ==="
grep -E '^(GEMINI_STATE|GEMINI_DETAIL|GEMINI_VERDICT|GEMINI_CONFIDENCE|GEMINI_THOUGHT_AT|GEMINI_THOUGHT_PACKAGE|GEMINI_REASON_TOKEN|GEMINI_THOUGHT)='   "$R/runtime/gemini_reasoner.env" 2>/dev/null || true

echo "=== CC THOUGHT ==="
awk '
  /^__THOUGHTS__$/ {on=1; next}
  /^__/ {if(on) exit}
  on {print}
' "$R/cc_snapshot" 2>/dev/null || true

echo "=== NEURONS ==="
grep -E '^(USED_EST|SUCCESS_CALLS)=' "$R/config/hermes_neuron_live.env" 2>/dev/null || true

echo "=== SAFETY ==="
grep -E '^(EXECUTOR_STATE|ACTIVE_DIGEST)=' "$R/runtime/execution.env" 2>/dev/null || true
