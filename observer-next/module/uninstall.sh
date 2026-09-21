#!/system/bin/sh
# DJAEGER AI Adaptive uninstall guard.
# Restore verified pre-apply CPU/GPU bounds before the Magisk module disappears.
MODDIR=${0%/*}
ROOT=/data/adb/djaeger_observer
EXEC="$MODDIR/bin/executor.sh"
REC="$ROOT/recovery"
mkdir -p "$REC" "$ROOT/runtime" 2>/dev/null

# Closing approval forces executor gate closed; existing backup must be restored.
rm -f "$ROOT/policy/approved.env"
if [ -r "$EXEC" ]; then
  if sh "$EXEC" "$ROOT" once >/dev/null 2>&1; then
    {
      echo "UNINSTALL_RESTORE=VERIFIED_OR_NOT_REQUIRED"
      echo "AT=$(date +%s)"
    } > "$REC/uninstall_restore.env"
    chmod 600 "$REC/uninstall_restore.env" 2>/dev/null
  else
    {
      echo "UNINSTALL_RESTORE=FAILED"
      echo "BACKUP_PRESERVED=$([ -r "$ROOT/runtime/execution_backup.env" ] && echo YES || echo NO)"
      echo "AT=$(date +%s)"
    } > "$REC/uninstall_restore.env"
    chmod 600 "$REC/uninstall_restore.env" 2>/dev/null
    # Persistent /data/adb/djaeger_observer is intentionally retained so the
    # recovery backup and credential allowlist survive a failed uninstall restore.
  fi
fi

for n in observer frame_observer learner gemini_reasoner hermes_adapter consensus shadow executor railway_bridge; do
  pkill -f "djaeger_ai_observer.*$n.sh" 2>/dev/null || true
done

# Do not remove persistent identity, Gemini vault, Hermes config, registries or
# recovery evidence. A later paired install can resume/restore them safely.
exit 0
