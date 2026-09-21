#!/system/bin/sh
MODDIR=${0%/*}
ROOT=/data/adb/djaeger_observer
mkdir -p "$ROOT/runtime" "$ROOT/history" "$ROOT/policy" "$ROOT/recovery" "$ROOT/config"
chmod 700 "$ROOT" "$ROOT/config" "$ROOT/recovery" 2>/dev/null

sh "$MODDIR/bin/migrate.sh" "$ROOT" "$MODDIR"

pkill -f "djaeger_ai_observer.*observer.sh" 2>/dev/null
pkill -f "djaeger_ai_observer.*agent_bus.sh" 2>/dev/null
pkill -f "djaeger_ai_observer.*executor.sh" 2>/dev/null

nohup sh "$MODDIR/bin/observer.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/agent_bus.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/executor.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
