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

# Never reuse a learned model or AI approval from an older evidence schema.
# Credentials, identity, registries and human feedback remain persistent.
if [ -r "$ROOT/history/learned_envelope.env" ] && ! grep -Fqx 'SCHEMA=DJAEGER_LEARNED_ENVELOPE_V3' "$ROOT/history/learned_envelope.env" 2>/dev/null; then
  mv -f "$ROOT/history/learned_envelope.env" "$ROOT/recovery/learned_envelope.pre-v3.$(date +%s).env" 2>/dev/null || rm -f "$ROOT/history/learned_envelope.env"
fi
rm -f "$ROOT/policy/gemini_proposal.env" "$ROOT/policy/hermes_local_vote.env" "$ROOT/policy/hermes_cloud_vote.env" "$ROOT/policy/hermes_proposal.env" "$ROOT/policy/candidate.env" "$ROOT/policy/approved.env"
rm -f "$ROOT/runtime/shadow.env" "$ROOT/runtime/consensus.env" "$ROOT/runtime/gemini_reasoner.env" "$ROOT/runtime/hermes_adapter.env"

migration_ready(){
  [ -r "$ROOT/recovery/migration.env" ] || return 1
  grep -Fqx 'MIGRATION_SCHEMA=9' "$ROOT/recovery/migration.env" 2>/dev/null || return 1
  grep -Fqx 'MIGRATION_STATE=RECOVERED' "$ROOT/recovery/migration.env" 2>/dev/null || return 1
  [ "$(sed -n 's/^KEY_[1-4]=//p' "$ROOT/config/gemini_vault.env" 2>/dev/null | awk 'NF{n++}END{print n+0}')" -eq 4 ] 2>/dev/null || return 1
  grep -Eq '^HERMES_ACCESS_KEY=.{20,}

for n in observer frame_observer learner gemini_reasoner hermes_adapter consensus shadow executor railway_bridge; do
  pkill -f "/djaeger_ai_observer/bin/$n.sh" 2>/dev/null || true
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

# Startup proof: publish whether critical workers actually came up.
sleep 1
{
  echo "STARTUP_SCHEMA=DJAEGER_STARTUP_V1"
  echo "STARTUP_AT=$(date +%s)"
  for n in observer frame_observer learner gemini_reasoner hermes_adapter consensus shadow executor; do
    if ps -A -o ARGS 2>/dev/null | grep -F "/djaeger_ai_observer/bin/$n.sh" | grep -v grep >/dev/null 2>&1; then
      echo "$(printf '%s' "$n" | tr '[:lower:]' '[:upper:]')=RUNNING"
    else
      echo "$(printf '%s' "$n" | tr '[:lower:]' '[:upper:]')=MISSING"
    fi
  done
} > "$ROOT/runtime/startup.env.tmp.$"
chmod 600 "$ROOT/runtime/startup.env.tmp.$" 2>/dev/null
mv -f "$ROOT/runtime/startup.env.tmp.$" "$ROOT/runtime/startup.env"
 "$ROOT/config/hermes_cloud.env" 2>/dev/null || return 1
  grep -Eq '^HERMES_ENDPOINT=https://' "$ROOT/config/hermes_cloud.env" 2>/dev/null || return 1
  return 0
}

if migration_ready; then
  :
else
  if command -v timeout >/dev/null 2>&1; then
    timeout 20 sh "$MODDIR/bin/migrate.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 || true
  else
    sh "$MODDIR/bin/migrate.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 || true
  fi
fi

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
