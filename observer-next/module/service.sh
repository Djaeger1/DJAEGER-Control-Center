#!/system/bin/sh
MODDIR=${0%/*}
ROOT=/data/adb/djaeger_observer
mkdir -p "$ROOT/runtime" "$ROOT/history" "$ROOT/policy" "$ROOT/recovery" "$ROOT/config"
chmod 700 "$ROOT" "$ROOT/config" "$ROOT/recovery" 2>/dev/null
[ -f "$ROOT/config/game_registry.tsv" ] || : > "$ROOT/config/game_registry.tsv"
[ -f "$ROOT/config/app_registry.tsv" ] || : > "$ROOT/config/app_registry.tsv"
chmod 600 "$ROOT/config/game_registry.tsv" "$ROOT/config/app_registry.tsv" 2>/dev/null

sh "$MODDIR/bin/migrate.sh" "$ROOT" "$MODDIR"

for n in observer frame_observer learner gemini_reasoner hermes_adapter consensus shadow; do
  pkill -f "djaeger_ai_observer.*$n.sh" 2>/dev/null
done

nohup sh "$MODDIR/bin/observer.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/frame_observer.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/learner.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/gemini_reasoner.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/hermes_adapter.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/consensus.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/shadow.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
