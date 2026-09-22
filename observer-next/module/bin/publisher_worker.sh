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

[ -r "$BIN_DIR/publisher.sh" ] || exit 1
. "$BIN_DIR/publisher.sh"

while true; do
  if [ -r "$ROOT/runtime/snapshot.env" ]; then
    publish_cc "$ROOT"
  fi

  WCLASS=$(sed -n 's/^WORKLOAD_CLASS=//p' "$ROOT/runtime/workload.env" 2>/dev/null | head -n1)
  if [ "$WCLASS" = GAME ]; then
    sleep 3
  else
    sleep 8
  fi
done
