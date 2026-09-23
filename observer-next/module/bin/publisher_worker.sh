#!/system/bin/sh
# Independent Control Center publisher.
# Keeps expensive publication work off the Device Truth observer cadence.

ROOT="$1"
MODDIR="$2"
BIN_DIR="${0%/*}"

if [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim publisher_worker
fi

# Keep the singleton claim authoritative for the full worker lifetime.
# If another generation legitimately replaces the lock owner, any stale
# publisher process self-terminates on its next loop instead of continuing
# as an invisible duplicate without lock ownership.
PUBLISHER_LOCK="$ROOT/runtime/locks/publisher_worker.lock/pid"
PUBLISHER_SELF="$(cat "$PUBLISHER_LOCK" 2>/dev/null)"
[ -n "$PUBLISHER_SELF" ] || exit 0

publisher_still_owns_lock(){
  [ "$(cat "$PUBLISHER_LOCK" 2>/dev/null)" = "$PUBLISHER_SELF" ]
}

[ -r "$BIN_DIR/publisher.sh" ] || exit 1
. "$BIN_DIR/publisher.sh"

# Lifecycle supervisor for ONE HERMES THOUGHT.
# service.sh already guarantees publisher_worker startup; this keeps the
# reasoning worker independent from publisher rendering while avoiding
# another privileged startup hook.
THOUGHT_BIN="$BIN_DIR/hermes_thought_worker.sh"
THOUGHT_LOCK="$ROOT/runtime/locks/hermes_thought_worker.lock/pid"
ensure_thought_worker(){
  [ -r "$THOUGHT_BIN" ] || return 0
  _tp="$(cat "$THOUGHT_LOCK" 2>/dev/null)"
  case "$_tp" in
    ""|*[!0-9]*) _tp=0 ;;
  esac
  if [ "$_tp" -gt 1 ] 2>/dev/null && kill -0 "$_tp" 2>/dev/null; then
    return 0
  fi
  nohup sh "$THOUGHT_BIN" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
}

CONTEXTUAL_SHADOW_BIN="$BIN_DIR/shadow_contextual_v4.sh"
CONTEXTUAL_SHADOW_LOCK="$ROOT/runtime/locks/shadow_contextual_v4.lock/pid"
ensure_contextual_shadow(){
  [ -r "$CONTEXTUAL_SHADOW_BIN" ] || return 0
  _sp="$(cat "$CONTEXTUAL_SHADOW_LOCK" 2>/dev/null)"
  case "$_sp" in
    ""|*[!0-9]*) _sp=0 ;;
  esac
  if [ "$_sp" -gt 1 ] 2>/dev/null && kill -0 "$_sp" 2>/dev/null; then
    return 0
  fi
  nohup sh "$CONTEXTUAL_SHADOW_BIN" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
}

ensure_contextual_shadow
ensure_thought_worker

while true; do
  publisher_still_owns_lock || exit 0
  ensure_contextual_shadow
  ensure_thought_worker
  if [ -r "$ROOT/runtime/snapshot.env" ]; then
    publish_cc "$ROOT"
  fi

  WCLASS=$(sed -n 's/^WORKLOAD_CLASS=//p' "$ROOT/runtime/workload.env" 2>/dev/null | head -n1)
  if [ "$WCLASS" = GAME ]; then
    sleep 3
  else
    sleep 8
  fi
  publisher_still_owns_lock || exit 0
done
