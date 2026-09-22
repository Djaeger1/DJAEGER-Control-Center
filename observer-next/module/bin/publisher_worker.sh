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

while true; do
  publisher_still_owns_lock || exit 0
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
