#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
W="$M/bin/hermes_thought_worker.sh"
REV=283d55a1b4d6ee4ef5715f7a7a77909174f6b338
URL="https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/$REV/runtime-patches/one_hermes_thought_worker_v3_4.sh"
TMP="$R/runtime/hermes_thought_worker_v3_4.new"
STATE="$R/runtime/hermes_thought_worker_state.env"
OUT="$R/runtime/hermes_thought.env"
HSTATE="$R/runtime/hermes_adapter.env"
ERR="$R/runtime/hermes_thought_worker.err"
LOCK="$R/runtime/locks/hermes_thought_worker.lock/pid"

curl -fsSL -m 30 "$URL" -o "$TMP" || { echo "WORKER_DOWNLOAD=FAIL"; exit 1; }
sh -n "$TMP" || { echo "WORKER_SYNTAX=FAIL"; exit 2; }
grep -Fq "WORKER_VERSION=ONE_HERMES_THOUGHT_V3_4" "$TMP" || { echo "WORKER_ID=MISSING"; exit 3; }
grep -Fq 'echo "PID=$$"' "$TMP" || { echo "PID_FIX=MISSING"; exit 4; }
grep -Fq '_ws_tmp="$WORKER_STATE.tmp.$$"' "$TMP" || { echo "STATE_TMP_FIX=MISSING"; exit 5; }

echo "WORKER_V3_4_SYNTAX=OK"
echo "PID_FIX=OK"
echo "STATE_TMP_FIX=OK"

TS=$(date +%s)
[ -r "$W" ] && cp "$W" "$R/runtime/hermes_thought_worker.pre_v3_4.$TS" || true
cp "$TMP" "$W" || exit 6
chmod 755 "$W"
rm -f "$TMP"

OLD=$(cat "$LOCK" 2>/dev/null)
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

# First prove the replacement worker is real and alive.
I=0
while [ "$I" -lt 12 ]; do
  V=$(sed -n "s/^WORKER_VERSION=//p" "$STATE" 2>/dev/null | head -n1)
  P=$(sed -n "s/^PID=//p" "$STATE" 2>/dev/null | head -n1)
  LP=$(cat "$LOCK" 2>/dev/null)
  case "$P:$LP" in
    *[!0-9:]*|"":*) ;;
    *) [ "$V" = ONE_HERMES_THOUGHT_V3_4 ] && [ "$P" = "$LP" ] && kill -0 "$P" 2>/dev/null && break ;;
  esac
  sleep 1
  I=$((I+1))
done

V=$(sed -n "s/^WORKER_VERSION=//p" "$STATE" 2>/dev/null | head -n1)
P=$(sed -n "s/^PID=//p" "$STATE" 2>/dev/null | head -n1)
LP=$(cat "$LOCK" 2>/dev/null)
case "$P" in ""|*[!0-9]*) LIVE=NO;; *) kill -0 "$P" 2>/dev/null && LIVE=YES || LIVE=NO;; esac

echo "PATCH=ONE_HERMES_THOUGHT_V3_4_ACTIVE"
echo "WORKER_VERSION=${V:-MISSING}"
echo "WORKER_PID=${P:-MISSING}"
echo "LOCK_PID=${LP:-MISSING}"
echo "WORKER_LIVE=$LIVE"

if [ "$V" != ONE_HERMES_THOUGHT_V3_4 ] || [ "$LIVE" != YES ] || [ "$P" != "$LP" ]; then
  echo "RUNTIME_VERIFY=FAIL_WORKER"
  echo "=== STATE ==="; cat "$STATE" 2>/dev/null || true
  echo "=== ERRLOG ==="; tail -n 20 "$ERR" 2>/dev/null || true
  exit 7
fi

# Give Hermes-owned cycles time to publish, but do not fail if another brain owns the cycle.
I=0
while [ "$I" -lt 25 ]; do
  AC=$(sed -n "s/^HERMES_ACTIVE_SOURCE=//p" "$HSTATE" 2>/dev/null | head -n1)
  TV=$(sed -n "s/^WORKER_VERSION=//p" "$OUT" 2>/dev/null | head -n1)
  PG=$(sed -n "s/^PROGRESS=//p" "$OUT" 2>/dev/null | head -n1)
  FC=$(sed -n "s/^FRAME_CLASS=//p" "$OUT" 2>/dev/null | head -n1)
  case "$AC" in
    HERMES_LOCAL|HERMES_H2|HERMES_CLOUD)
      [ "$TV" = ONE_HERMES_THOUGHT_V3_4 ] && [ -n "$PG" ] && [ -n "$FC" ] && break
      ;;
    *) break ;;
  esac
  sleep 1
  I=$((I+1))
done

AC=$(sed -n "s/^HERMES_ACTIVE_SOURCE=//p" "$HSTATE" 2>/dev/null | head -n1)
LS=$(sed -n "s/^HERMES_LOCAL_STATE=//p" "$HSTATE" 2>/dev/null | head -n1)
CD=$(sed -n "s/^HERMES_CLOUD_DETAIL=//p" "$HSTATE" 2>/dev/null | head -n1)
ST=$(sed -n "s/^LAST_STAGE=//p" "$STATE" 2>/dev/null | head -n1)
TV=$(sed -n "s/^WORKER_VERSION=//p" "$OUT" 2>/dev/null | head -n1)
PG=$(sed -n "s/^PROGRESS=//p" "$OUT" 2>/dev/null | head -n1)
FC=$(sed -n "s/^FRAME_CLASS=//p" "$OUT" 2>/dev/null | head -n1)

echo "HERMES_ACTIVE_SOURCE=${AC:-NONE}"
echo "HERMES_LOCAL_STATE=${LS:-MISSING}"
echo "HERMES_DETAIL=${CD:-MISSING}"
echo "LAST_STAGE=${ST:-MISSING}"
echo "THOUGHT_WORKER_VERSION=${TV:-MISSING}"

case "$AC" in
  HERMES_LOCAL|HERMES_H2|HERMES_CLOUD)
    if [ "$TV" = ONE_HERMES_THOUGHT_V3_4 ] && [ -n "$PG" ] && [ -n "$FC" ]; then
      echo "RUNTIME_VERIFY=OK"
    else
      echo "RUNTIME_VERIFY=FAIL_PUBLISH"
      echo "=== STATE ==="; cat "$STATE" 2>/dev/null || true
      echo "=== ERRLOG ==="; tail -n 20 "$ERR" 2>/dev/null || true
      exit 8
    fi
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
