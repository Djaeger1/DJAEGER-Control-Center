#!/system/bin/sh
MODDIR=${0%/*}
ROOT=/data/adb/djaeger_observer
mkdir -p "$ROOT/runtime" "$ROOT/history" "$ROOT/policy" "$ROOT/recovery" "$ROOT/config"
chmod 700 "$ROOT" "$ROOT/config" "$ROOT/recovery" 2>/dev/null
[ -f "$ROOT/config/game_registry.tsv" ] || : > "$ROOT/config/game_registry.tsv"
[ -f "$ROOT/config/app_registry.tsv" ] || : > "$ROOT/config/app_registry.tsv"
[ -f "$ROOT/config/execution_mode" ] || echo AUTO > "$ROOT/config/execution_mode"
chmod 600 "$ROOT/config/game_registry.tsv" "$ROOT/config/app_registry.tsv" "$ROOT/config/execution_mode" 2>/dev/null
# A verified pair must be re-established by the currently running APK after
# every module service start. Never inherit a stale MATCHED claim.
rm -f "$ROOT/runtime/handshake.env"

sh "$MODDIR/bin/migrate.sh" "$ROOT" "$MODDIR"

for n in observer frame_observer learner gemini_reasoner hermes_adapter consensus shadow executor railway_bridge; do
  pkill -f "djaeger_ai_observer.*$n.sh" 2>/dev/null || true
done

nohup sh "$MODDIR/bin/observer.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/frame_observer.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/learner.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/gemini_reasoner.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/hermes_adapter.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/consensus.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/shadow.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/executor.sh" "$ROOT" daemon >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/railway_bridge.sh" "$ROOT" daemon >/dev/null 2>&1 &
