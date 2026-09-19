#!/system/bin/sh
ROOT="$1"; VER="$2"; PREV="$3"; DEST="$ROOT/releases/$VER"; LOG="$ROOT/logs/handoff.log"; PID="$ROOT/state/workd.pid"
PORT=8766
ts(){ date '+%Y-%m-%dT%H:%M:%S%z'; }
log(){ echo "$(ts) $*" >> "$LOG"; }

# Stop every orphan HERMES WORK workd, not unrelated processes.
for P in /proc/[0-9]*; do
  N="${P#/proc/}"
  [ "$N" = "$$" ] && continue
  CMD="$(tr '\000' ' ' < "$P/cmdline" 2>/dev/null)"
  case "$CMD" in
    *"$ROOT/releases/"*"/bin/workd"* ) kill "$N" 2>/dev/null ;;
  esac
done

# Give the old listener time to release 8766.
TRY=0
while [ "$TRY" -lt 10 ]; do
  /system/bin/wget -qO- "http://127.0.0.1:$PORT/api/work/status" >/dev/null 2>&1 || break
  sleep 1; TRY=$((TRY+1))
done

nohup "$DEST/bin/workd" --root "$ROOT" --release "$DEST" >>"$ROOT/logs/workd.log" 2>&1 &
NEW=$!
echo "$NEW" > "$PID"

HEALTHY=0
TRY=0
while [ "$TRY" -lt 20 ]; do
  sleep 1
  if ! kill -0 "$NEW" 2>/dev/null; then break; fi
  J="$(/system/bin/wget -qO- "http://127.0.0.1:$PORT/api/work/status" 2>/dev/null)"
  if printf '%s' "$J" | grep -Fq "\"release\":\"$VER\""; then HEALTHY=1; break; fi
  TRY=$((TRY+1))
done

if [ "$HEALTHY" = 1 ]; then
  # Promotion is atomic and happens only after the target binary answers as itself.
  printf '%s\n' "$VER" > "$ROOT/current_release"
  [ -n "$PREV" ] && [ "$PREV" != "$VER" ] && printf '%s\n' "$PREV" > "$ROOT/previous_release"
  APID="$ROOT/state/autoupdate.pid"
  AUP="$DEST/worker/autoupdate.sh"
  if [ -f "$AUP" ]; then
    OLD_AUP="$(cat "$APID" 2>/dev/null)"
    if [ -z "$OLD_AUP" ] || ! kill -0 "$OLD_AUP" 2>/dev/null; then
      HERMES_ROOT="$ROOT" nohup /system/bin/sh "$AUP" >>"$ROOT/logs/autoupdate.log" 2>&1 &
      echo $! > "$APID"
    fi
  fi
  log "PASS $VER pid=$NEW verified_release=$VER"
  exit 0
fi

log "FAIL $VER rollback=$PREV"
kill "$NEW" 2>/dev/null
sleep 1
if [ -n "$PREV" ] && [ -x "$ROOT/releases/$PREV/bin/workd" ]; then
  nohup "$ROOT/releases/$PREV/bin/workd" --root "$ROOT" --release "$ROOT/releases/$PREV" >>"$ROOT/logs/workd.log" 2>&1 &
  RP=$!; echo "$RP" > "$PID"
  RTRY=0
  while [ "$RTRY" -lt 15 ]; do
    sleep 1
    RJ="$(/system/bin/wget -qO- "http://127.0.0.1:$PORT/api/work/status" 2>/dev/null)"
    if printf '%s' "$RJ" | grep -Fq "\"release\":\"$PREV\""; then
      printf '%s\n' "$PREV" > "$ROOT/current_release"
      log "ROLLBACK_PASS $PREV pid=$RP"
      exit 1
    fi
    RTRY=$((RTRY+1))
  done
fi
log "ROLLBACK_FAIL target=$VER prev=$PREV"
exit 1
