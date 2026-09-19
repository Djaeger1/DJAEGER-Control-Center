#!/system/bin/sh
ROOT="$1"; VER="$2"; PREV="$3"; DEST="$ROOT/releases/$VER"; LOG="$ROOT/logs/handoff.log"; PID="$ROOT/state/workd.pid"
sleep 1
OLD="$(cat "$PID" 2>/dev/null)"
[ -n "$OLD" ] && kill "$OLD" 2>/dev/null
sleep 1
nohup "$DEST/bin/workd" --root "$ROOT" --release "$DEST" >>"$ROOT/logs/workd.log" 2>&1 &
NEW=$!; echo "$NEW" > "$PID"; sleep 2
if kill -0 "$NEW" 2>/dev/null && /system/bin/wget -qO- http://127.0.0.1:8766/api/work/status >/dev/null 2>&1; then
  APID="$ROOT/state/autoupdate.pid"
  AUP="$DEST/worker/autoupdate.sh"
  if [ -f "$AUP" ]; then
    OLD_AUP="$(cat "$APID" 2>/dev/null)"
    if [ -z "$OLD_AUP" ] || ! kill -0 "$OLD_AUP" 2>/dev/null; then
      HERMES_ROOT="$ROOT" nohup /system/bin/sh "$AUP" >>"$ROOT/logs/autoupdate.log" 2>&1 &
      echo $! > "$APID"
    fi
  fi
  echo "$(date) PASS $VER pid=$NEW" >>"$LOG"; exit 0
fi
echo "$(date) FAIL $VER rollback=$PREV" >>"$LOG"; kill "$NEW" 2>/dev/null
if [ -n "$PREV" ] && [ -x "$ROOT/releases/$PREV/bin/workd" ]; then
  printf '%s\n' "$PREV" >"$ROOT/current_release"
  nohup "$ROOT/releases/$PREV/bin/workd" --root "$ROOT" --release "$ROOT/releases/$PREV" >>"$ROOT/logs/workd.log" 2>&1 &
  echo $! >"$PID"
fi
exit 1
