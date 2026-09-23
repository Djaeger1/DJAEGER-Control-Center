#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
W="$M/bin/hermes_thought_worker.sh"
REV=bdbb565bfc46bd8d408c4cd04072a4d2a850cc10
URL="https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/$REV/runtime-patches/one_hermes_thought_worker_v3_1.sh"
TMP="$R/runtime/hermes_thought_worker_v3_1.new"
STATE="$R/runtime/hermes_thought_worker_state.env"

curl -fsSL -m 30 "$URL" -o "$TMP" || { echo "WORKER_DOWNLOAD=FAIL"; exit 1; }
sh -n "$TMP" || { echo "WORKER_SYNTAX=FAIL"; exit 2; }
grep -Fq "WORKER_VERSION=ONE_HERMES_THOUGHT_V3_1" "$TMP" || { echo "WORKER_ID=MISSING"; exit 3; }
grep -Fq "ONE_HERMES_LOCAL_PROGRESS_V1" "$TMP" || { echo "LOCAL_PROGRESS=MISSING"; exit 4; }

echo "WORKER_V3_1_SYNTAX=OK"
echo "SELF_ID=OK"
echo "LOCAL_PROGRESS=OK"

TS=$(date +%s)
[ -r "$W" ] && cp "$W" "$R/runtime/hermes_thought_worker.pre_v3_1.$TS" || true
cp "$TMP" "$W" || exit 5
chmod 755 "$W"
rm -f "$TMP"

SELF=$$
for D in /proc/[0-9]*; do
  P=${D#/proc/}
  [ "$P" = "$SELF" ] && continue
  C=$(tr "\000" " " < "$D/cmdline" 2>/dev/null || true)
  case "$C" in
    *"/data/adb/modules/djaeger_ai_observer/bin/hermes_thought_worker.sh"*"/data/adb/djaeger_observer"*)
      kill -TERM "$P" 2>/dev/null || true
      ;;
  esac
done
sleep 1
for D in /proc/[0-9]*; do
  P=${D#/proc/}
  [ "$P" = "$SELF" ] && continue
  C=$(tr "\000" " " < "$D/cmdline" 2>/dev/null || true)
  case "$C" in
    *"/data/adb/modules/djaeger_ai_observer/bin/hermes_thought_worker.sh"*"/data/adb/djaeger_observer"*)
      kill -KILL "$P" 2>/dev/null || true
      ;;
  esac
done

rm -rf "$R/runtime/locks/hermes_thought_worker.lock"
rm -f "$STATE" "$R/runtime/hermes_thought_progress.env"
nohup sh "$W" "$R" "$M" >/dev/null 2>&1 &

I=0
while [ "$I" -lt 10 ]; do
  V=$(sed -n "s/^WORKER_VERSION=//p" "$STATE" 2>/dev/null | head -n1)
  [ "$V" = ONE_HERMES_THOUGHT_V3_1 ] && break
  sleep 1
  I=$((I+1))
done

V=$(sed -n "s/^WORKER_VERSION=//p" "$STATE" 2>/dev/null | head -n1)
P=$(sed -n "s/^PID=//p" "$STATE" 2>/dev/null | head -n1)
H=$(sed -n "s/^HEARTBEAT_AT=//p" "$STATE" 2>/dev/null | head -n1)

echo "PATCH=ONE_HERMES_THOUGHT_V3_1_ACTIVE"
echo "WORKER_VERSION=${V:-MISSING}"
echo "WORKER_PID=${P:-MISSING}"
echo "HEARTBEAT_AT=${H:-MISSING}"

if [ "$V" != ONE_HERMES_THOUGHT_V3_1 ]; then
  echo "WORKER_VERIFY=FAIL"
  exit 6
fi

echo "WORKER_VERIFY=OK"
echo "=== THOUGHT ==="
grep -E "^(WORKER_VERSION|WORKER_PID|FINGERPRINT|ORIGIN|STATUS|CONFIDENCE|REASON|PROGRESS|FRAME_CLASS|EVIDENCE|TEXT)=" "$R/runtime/hermes_thought.env" 2>/dev/null || echo "THOUGHT=WAITING"
echo "=== NEURONS ==="
grep -E "^(USED_EST|SUCCESS_CALLS)=" "$R/config/hermes_neuron_live.env" 2>/dev/null || true
echo "=== SAFETY ==="
grep -E "^(EXECUTOR_STATE|ACTIVE_DIGEST)=" "$R/runtime/execution.env" 2>/dev/null || true
