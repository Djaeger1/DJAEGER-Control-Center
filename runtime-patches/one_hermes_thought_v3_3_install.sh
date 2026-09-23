#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
W="$M/bin/hermes_thought_worker.sh"
REV=13da17b1eafaba8f6dd3d3faecb4738f3ad9212b
URL="https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/$REV/runtime-patches/one_hermes_thought_worker_v3_3.sh"
TMP="$R/runtime/hermes_thought_worker_v3_3.new"
STATE="$R/runtime/hermes_thought_worker_state.env"
OUT="$R/runtime/hermes_thought.env"
ERR="$R/runtime/hermes_thought_worker.err"

curl -fsSL -m 30 "$URL" -o "$TMP" || { echo "WORKER_DOWNLOAD=FAIL"; exit 1; }
sh -n "$TMP" || { echo "WORKER_SYNTAX=FAIL"; exit 2; }
grep -Fq "WORKER_VERSION=ONE_HERMES_THOUGHT_V3_3" "$TMP" || { echo "WORKER_ID=MISSING"; exit 3; }
grep -Fq "worker_state PUBLISHED NONE" "$TMP" || { echo "PUBLISH_TRACE=MISSING"; exit 4; }
grep -Fq "WAITING_NON_HERMES" "$TMP" || { echo "ACTIVE_SOURCE_TRACE=MISSING"; exit 5; }

echo "WORKER_V3_3_SYNTAX=OK"
echo "PUBLISH_TRACE=OK"
echo "ACTIVE_SOURCE_TRACE=OK"

TS=$(date +%s)
[ -r "$W" ] && cp "$W" "$R/runtime/hermes_thought_worker.pre_v3_3.$TS" || true
cp "$TMP" "$W" || exit 6
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
rm -f "$STATE" "$R/runtime/hermes_thought_progress.env" "$ERR"
nohup sh "$W" "$R" "$M" >/dev/null 2>&1 &

I=0
while [ "$I" -lt 35 ]; do
  V=$(sed -n "s/^WORKER_VERSION=//p" "$STATE" 2>/dev/null | head -n1)
  ST=$(sed -n "s/^LAST_STAGE=//p" "$STATE" 2>/dev/null | head -n1)
  AC=$(sed -n "s/^ACTIVE_SOURCE=//p" "$STATE" 2>/dev/null | head -n1)
  TV=$(sed -n "s/^WORKER_VERSION=//p" "$OUT" 2>/dev/null | head -n1)
  if [ "$V" = ONE_HERMES_THOUGHT_V3_3 ]; then
    case "$AC:$ST" in
      HERMES_LOCAL:PUBLISHED|HERMES_H2:PUBLISHED|HERMES_CLOUD:PUBLISHED)
        [ "$TV" = ONE_HERMES_THOUGHT_V3_3 ] && break
        ;;
      *:WAITING_NON_HERMES) break ;;
    esac
  fi
  sleep 1
  I=$((I+1))
done

V=$(sed -n "s/^WORKER_VERSION=//p" "$STATE" 2>/dev/null | head -n1)
P=$(sed -n "s/^PID=//p" "$STATE" 2>/dev/null | head -n1)
HB=$(sed -n "s/^HEARTBEAT_AT=//p" "$STATE" 2>/dev/null | head -n1)
AC=$(sed -n "s/^ACTIVE_SOURCE=//p" "$STATE" 2>/dev/null | head -n1)
ST=$(sed -n "s/^LAST_STAGE=//p" "$STATE" 2>/dev/null | head -n1)
ER=$(sed -n "s/^LAST_ERROR=//p" "$STATE" 2>/dev/null | head -n1)
TV=$(sed -n "s/^WORKER_VERSION=//p" "$OUT" 2>/dev/null | head -n1)
PG=$(sed -n "s/^PROGRESS=//p" "$OUT" 2>/dev/null | head -n1)
FC=$(sed -n "s/^FRAME_CLASS=//p" "$OUT" 2>/dev/null | head -n1)

echo "PATCH=ONE_HERMES_THOUGHT_V3_3_ACTIVE"
echo "WORKER_VERSION=${V:-MISSING}"
echo "WORKER_PID=${P:-MISSING}"
echo "HEARTBEAT_AT=${HB:-MISSING}"
echo "ACTIVE_SOURCE=${AC:-MISSING}"
echo "LAST_STAGE=${ST:-MISSING}"
echo "LAST_ERROR=${ER:-MISSING}"
echo "THOUGHT_WORKER_VERSION=${TV:-MISSING}"

case "$P" in ""|*[!0-9]*) LIVE=NO;; *) kill -0 "$P" 2>/dev/null && LIVE=YES || LIVE=NO;; esac
echo "WORKER_LIVE=$LIVE"

if [ "$LIVE" != YES ] || [ "$V" != ONE_HERMES_THOUGHT_V3_3 ]; then
  echo "RUNTIME_VERIFY=FAIL_WORKER"
  echo "=== ERRLOG ==="; tail -n 20 "$ERR" 2>/dev/null || true
  exit 7
fi

case "$AC" in
  HERMES_LOCAL|HERMES_H2|HERMES_CLOUD)
    if [ "$ST" != PUBLISHED ] || [ "$TV" != ONE_HERMES_THOUGHT_V3_3 ] || [ -z "$PG" ] || [ -z "$FC" ]; then
      echo "RUNTIME_VERIFY=FAIL_PUBLISH"
      echo "=== ERRLOG ==="; tail -n 20 "$ERR" 2>/dev/null || true
      exit 8
    fi
    echo "RUNTIME_VERIFY=OK"
    ;;
  *)
    echo "RUNTIME_VERIFY=DEFERRED_NON_HERMES"
    ;;
esac

echo "=== THOUGHT ==="
grep -E "^(WORKER_VERSION|WORKER_PID|FINGERPRINT|ORIGIN|STATUS|CONFIDENCE|REASON|PROGRESS|FRAME_CLASS|EVIDENCE|TEXT)=" "$OUT" 2>/dev/null || true
echo "=== NEURONS ==="
grep -E "^(USED_EST|SUCCESS_CALLS)=" "$R/config/hermes_neuron_live.env" 2>/dev/null || true
echo "=== SAFETY ==="
grep -E "^(EXECUTOR_STATE|ACTIVE_DIGEST)=" "$R/runtime/execution.env" 2>/dev/null || true
