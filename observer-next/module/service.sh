#!/system/bin/sh
MODDIR="$(dirname "$0")"
ROOT=/data/adb/djaeger_observer

mkdir -p "$ROOT/runtime" "$ROOT/history" "$ROOT/policy" "$ROOT/recovery" "$ROOT/config"
chmod 700 "$ROOT" "$ROOT/config" "$ROOT/recovery" 2>/dev/null
[ -f "$ROOT/config/game_registry.tsv" ] || : > "$ROOT/config/game_registry.tsv"
[ -f "$ROOT/config/app_registry.tsv" ] || : > "$ROOT/config/app_registry.tsv"
[ -f "$ROOT/config/execution_mode" ] || echo AUTO > "$ROOT/config/execution_mode"
chmod 600 "$ROOT/config/game_registry.tsv" "$ROOT/config/app_registry.tsv" "$ROOT/config/execution_mode" 2>/dev/null

# Pair must be re-established by the currently running APK after every service start.
rm -f "$ROOT/runtime/handshake.env"

# Never reuse stale AI approvals from an older evidence/runtime session.
if [ -r "$ROOT/history/learned_envelope.env" ] && ! grep -Fqx 'SCHEMA=DJAEGER_LEARNED_ENVELOPE_V3' "$ROOT/history/learned_envelope.env" 2>/dev/null; then
  mv -f "$ROOT/history/learned_envelope.env" "$ROOT/recovery/learned_envelope.pre-v3.$(date +%s).env" 2>/dev/null || rm -f "$ROOT/history/learned_envelope.env"
fi
rm -f "$ROOT/policy/gemini_proposal.env" "$ROOT/policy/hermes_local_vote.env" "$ROOT/policy/hermes_cloud_vote.env" "$ROOT/policy/hermes_proposal.env" "$ROOT/policy/candidate.env" "$ROOT/policy/approved.env"
rm -f "$ROOT/runtime/shadow.env" "$ROOT/runtime/consensus.env" "$ROOT/runtime/gemini_reasoner.env" "$ROOT/runtime/hermes_adapter.env"

migration_ready(){
  [ -r "$ROOT/recovery/migration.env" ] || return 1
  grep -Fqx 'MIGRATION_SCHEMA=9' "$ROOT/recovery/migration.env" 2>/dev/null || return 1
  grep -Fqx 'MIGRATION_STATE=RECOVERED' "$ROOT/recovery/migration.env" 2>/dev/null || return 1

  key_count="$(sed -n 's/^KEY_[1-4]=//p' "$ROOT/config/gemini_vault.env" 2>/dev/null | awk 'NF{n++}END{print n+0}')"
  [ "$key_count" -eq 4 ] 2>/dev/null || return 1
  grep -q '^HERMES_ACCESS_KEY=' "$ROOT/config/hermes_cloud.env" 2>/dev/null || return 1
  grep -q '^HERMES_ENDPOINT=https://' "$ROOT/config/hermes_cloud.env" 2>/dev/null || return 1
  return 0
}

stop_worker(){
  _name="$1"
  _target="$MODDIR/bin/$_name.sh"
  ps -A -o PID,ARGS 2>/dev/null | awk -v p="$_target" '$2=="sh" && $3==p {print $1}' | while IFS= read -r _pid; do
    [ -n "$_pid" ] && kill -TERM "$_pid" 2>/dev/null || true
  done
}

kill_worker_hard(){
  _name="$1"
  _target="$MODDIR/bin/$_name.sh"
  ps -A -o PID,ARGS 2>/dev/null | awk -v p="$_target" '$2=="sh" && $3==p {print $1}' | while IFS= read -r _pid; do
    [ -n "$_pid" ] && kill -KILL "$_pid" 2>/dev/null || true
  done
}

# A previous broad recovery scan must never outlive a new service generation.
stop_worker migrate
sleep 1
kill_worker_hard migrate

# Recovery scan is only needed when credentials are not already recovered.
# Never let broad legacy scanning block the runtime forever.
if ! migration_ready; then
  if command -v timeout >/dev/null 2>&1; then
    timeout 20 sh "$MODDIR/bin/migrate.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 || true
  else
    sh "$MODDIR/bin/migrate.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 || true
  fi
fi

# Stop every previous generation before clearing singleton locks.
for n in observer frame_observer network_observer learner gemini_reasoner hermes_adapter consensus shadow executor railway_bridge; do
  stop_worker "$n"
done
sleep 1
for n in observer frame_observer network_observer learner gemini_reasoner hermes_adapter consensus shadow executor railway_bridge; do
  kill_worker_hard "$n"
done
sleep 1

rm -rf "$ROOT/runtime/locks" 2>/dev/null
mkdir -p "$ROOT/runtime/locks"
chmod 700 "$ROOT/runtime/locks" 2>/dev/null

nohup sh "$MODDIR/bin/observer.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/frame_observer.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/network_observer.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/learner.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/gemini_reasoner.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/hermes_adapter.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/consensus.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/shadow.sh" "$ROOT" "$MODDIR" >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/executor.sh" "$ROOT" daemon >/dev/null 2>&1 &
nohup sh "$MODDIR/bin/railway_bridge.sh" "$ROOT" daemon >/dev/null 2>&1 &

# Publish a bounded startup proof for Control Center / diagnostics.
sleep 1
startup_tmp="$ROOT/runtime/startup.env.tmp.$$"
{
  echo "STARTUP_SCHEMA=DJAEGER_STARTUP_V2"
  echo "STARTUP_AT=$(date +%s)"
  echo "SINGLETON_GUARD=ENABLED"
  echo "PREVIOUS_GENERATION=TERMINATED"
  for n in observer frame_observer network_observer learner gemini_reasoner hermes_adapter consensus shadow executor; do
    if ps -A -o ARGS 2>/dev/null | grep -F "/djaeger_ai_observer/bin/$n.sh" | grep -v grep >/dev/null 2>&1; then
      state=RUNNING
    else
      state=MISSING
    fi
    upper="$(printf '%s' "$n" | tr '[:lower:]' '[:upper:]')"
    echo "$upper=$state"
  done
} > "$startup_tmp"
chmod 600 "$startup_tmp" 2>/dev/null
mv -f "$startup_tmp" "$ROOT/runtime/startup.env"
exit 0
