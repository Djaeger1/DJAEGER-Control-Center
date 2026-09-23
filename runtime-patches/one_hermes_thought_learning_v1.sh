#!/system/bin/sh
set -u
R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
P="$M/bin/publisher.sh"
H="$M/bin/hermes_adapter.sh"
W="$R/runtime/one_hermes_thought_learning_v1"
WORKER="$W/hermes_thought_worker.sh"
PN="$W/publisher.new"
SNIP="$W/publisher.snip"
REV=292874917cf54a6d96e4eec8e8e214142e2cb1f1
URL="https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/$REV/runtime-patches/one_hermes_thought_worker_v1.sh"
mkdir -p "$W" || exit 1

[ -r "$P" ] || { echo "PUBLISHER_SOURCE=MISSING"; exit 2; }
[ -r "$H" ] || { echo "HERMES_SOURCE=MISSING"; exit 3; }
grep -Fq 'FRAME_RECOVERY_CAUSAL_GATE_V1' "$H" || { echo "CAUSAL_RUNTIME=NOT_PRESENT"; exit 4; }

curl -fsSL -m 30 "$URL" -o "$WORKER" || { echo "WORKER_DOWNLOAD=FAIL"; exit 5; }
sh -n "$WORKER" || { echo "WORKER_SYNTAX=FAIL"; exit 6; }
echo "WORKER_SYNTAX=OK"

cat > "$SNIP" <<'SNIP'
  # ONE_HERMES_THOUGHT_PUBLISHER_V1
  # Publisher is display-only: ONE HERMES owns reasoning text.
  case "$_hactive" in
    HERMES_LOCAL|HERMES_H2|HERMES_CLOUD)
      _ht="$_root/runtime/hermes_thought.env"
      if [ -r "$_ht" ]; then
        _ht_at="$(pub_kv AT "$_ht")"; case "$_ht_at" in ''|*[!0-9]*) _ht_at=0;; esac
        _ht_age=$((_now-_ht_at)); [ "$_ht_age" -ge 0 ] 2>/dev/null || _ht_age=999999
        _ht_pkg="$(pub_kv PACKAGE "$_ht")"
        _ht_text="$(pub_kv TEXT "$_ht")"
        if [ "$_ht_pkg" = "$_pkg" ] && [ "$_ht_age" -le 180 ] 2>/dev/null && [ -n "$_ht_text" ]; then
          _thought_source=HERMES_H2
          _thought_status="$(pub_kv STATUS "$_ht")"; [ -n "$_thought_status" ] || _thought_status=DEPUTY_LOCAL_OBSERVE
          _thought_conf="$(pub_kv CONFIDENCE "$_ht")"; case "$_thought_conf" in ''|*[!0-9]*) _thought_conf=0;; esac
          _thought_reason="$(pub_kv REASON "$_ht")"; [ -n "$_thought_reason" ] || _thought_reason=ONE_HERMES_LOCAL_REASONING
          _thought_evidence="$(pub_kv EVIDENCE "$_ht")"
          _thought="$_ht_text"
          _thought_age="$_ht_age"
        fi
      fi
      ;;
  esac
SNIP

if grep -Fq 'ONE_HERMES_THOUGHT_PUBLISHER_V1' "$P"; then
  cp "$P" "$PN" || exit 11
  echo "PUBLISHER_OVERRIDE=ALREADY_PRESENT"
else
  C=$(grep -c '^  _thought_fresh=0;' "$P" 2>/dev/null || true)
  echo "PUBLISHER_ANCHORS=$C"
  [ "$C" = 1 ] || exit 12
  awk -v S="$SNIP" '
    BEGIN{done=0}
    {
      if(!done && index($0,"  _thought_fresh=0;")==1){
        while((getline x < S)>0) print x
        close(S); done=1
      }
      print
    }
    END{if(!done) exit 13}
  ' "$P" > "$PN" || exit 13
  echo "PUBLISHER_OVERRIDE=INSERTED"
fi

sh -n "$PN" || { echo "PUBLISHER_SYNTAX=FAIL"; exit 14; }
grep -Fq 'ONE_HERMES_THOUGHT_PUBLISHER_V1' "$PN" || exit 15
echo "PUBLISHER_SYNTAX=OK"

TS=$(date +%s)
cp "$P" "$R/runtime/publisher.pre_one_hermes_thought.$TS" || exit 21
cp "$PN" "$P" || exit 22
cp "$WORKER" "$M/bin/hermes_thought_worker.sh" || exit 23
chmod 755 "$P" "$M/bin/hermes_thought_worker.sh"

for N in hermes_thought_worker publisher_worker; do
  PID=$(cat "$R/runtime/locks/$N.lock/pid" 2>/dev/null)
  case "$PID" in ''|*[!0-9]*) ;; *) kill -TERM "$PID" 2>/dev/null; sleep 1; kill -0 "$PID" 2>/dev/null && kill -KILL "$PID" 2>/dev/null;; esac
  rm -rf "$R/runtime/locks/$N.lock"
done

nohup sh "$M/bin/hermes_thought_worker.sh" "$R" "$M" >/dev/null 2>&1 &
nohup sh "$M/bin/publisher_worker.sh" "$R" "$M" >/dev/null 2>&1 &
sleep 5

echo "PATCH=ONE_HERMES_THOUGHT_LEARNING_V1_ACTIVE"
echo "CLOUD_TEACHER=FAST_NOVEL_EVENT_ONLY"
echo "LOCAL_MEMORY_REUSE=ENABLED"
echo "CLOUD_LIMIT_FALLBACK=ENABLED"
echo "PUBLISHER=DISPLAY_ONLY"
echo "=== THOUGHT ==="
if [ -r "$R/runtime/hermes_thought.env" ]; then
  grep -E '^(ORIGIN|STATUS|CONFIDENCE|REASON|TEXT|FINGERPRINT)=' "$R/runtime/hermes_thought.env" || true
else
  echo "THOUGHT=WAITING_FOR_HERMES_STATE"
fi
echo "=== NEURONS ==="
grep -E '^(USED_EST|SUCCESS_CALLS)=' "$R/config/hermes_neuron_live.env" 2>/dev/null || true
echo "=== SAFETY ==="
grep -E '^(EXECUTOR_STATE|ACTIVE_DIGEST)=' "$R/runtime/execution.env" 2>/dev/null || true
