#!/system/bin/sh

# Small typed bridge used by the DJAEGER AI APK.
# Hardware writes remain owned exclusively by the local gated executor daemon.

ROOT=${DJAEGER_OBSERVER_ROOT:-/data/adb/djaeger_observer}
MODDIR=$(CDPATH= cd -- "${0%/*}/.." 2>/dev/null && pwd)
CONFIG="$ROOT/config"
RUNTIME="$ROOT/runtime"
HISTORY="$ROOT/history"
RECOVERY="$ROOT/recovery"
GEMINI_VAULT="$CONFIG/gemini_vault.env"
GEMINI_SLOT="$CONFIG/gemini_slot"
GAME_REGISTRY="$CONFIG/game_registry.tsv"
APP_REGISTRY="$CONFIG/app_registry.tsv"
HANDSHAKE="$RUNTIME/handshake.env"
GEMINI_COOLDOWN="$CONFIG/gemini_cooldown.env"

mkdir -p "$CONFIG" "$RUNTIME" "$HISTORY" "$RECOVERY"
chmod 700 "$ROOT" "$CONFIG" "$RECOVERY" 2>/dev/null

kv() { sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
clean_field() { printf '%s' "$1" | tr '\r\n\t|' '    ' | tr -cd 'A-Za-z0-9._:+/%=,@ -' | cut -c1-120; }
valid_package() { printf '%s\n' "$1" | grep -Eq '^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$'; }

vault_values() {
  sed -n 's/^KEY_[1-4]=//p' "$GEMINI_VAULT" 2>/dev/null | awk 'NF && !seen[$0]++' | head -n4
}

write_vault_from() {
  src="$1"; tmp="$GEMINI_VAULT.tmp.$$"
  awk 'NF && !seen[$0]++ {n++; if(n<=4) print "KEY_" n "=" $0}' "$src" > "$tmp"
  chmod 600 "$tmp"; mv -f "$tmp" "$GEMINI_VAULT"
  count=$(vault_values | wc -l | tr -d ' ')
  case "$count" in ''|*[!0-9]*) count=0;; esac
  slot=$(cat "$GEMINI_SLOT" 2>/dev/null)
  case "$slot" in ''|*[!0-9]*) slot=1;; esac
  if [ "$count" -eq 0 ]; then rm -f "$GEMINI_SLOT"
  elif [ "$slot" -lt 1 ] || [ "$slot" -gt "$count" ]; then echo 1 > "$GEMINI_SLOT"; chmod 600 "$GEMINI_SLOT"
  fi
}

read_key() {
  IFS= read -r key || true
  key=$(printf '%s' "$key" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  bytes=$(printf '%s' "$key" | wc -c | tr -d ' ')
  case "$bytes" in ''|*[!0-9]*) bytes=0;; esac
  [ "$bytes" -ge 20 ] && [ "$bytes" -le 256 ] || { echo "KEY_REJECTED=LENGTH"; exit 2; }
  case "$key" in *[!A-Za-z0-9._-]*) echo "KEY_REJECTED=FORMAT"; exit 2;; esac
}

add_key() {
  read_key
  vals="$RUNTIME/.vault_values.$$"
  vault_values > "$vals"
  if grep -Fqx "$key" "$vals" 2>/dev/null; then rm -f "$vals"; echo "KEY_STATUS=ALREADY_PRESENT"; return 0; fi
  count=$(wc -l < "$vals" 2>/dev/null); case "$count" in ''|*[!0-9]*) count=0;; esac
  [ "$count" -lt 4 ] || { rm -f "$vals"; echo "KEY_REJECTED=VAULT_FULL"; return 2; }
  printf '%s\n' "$key" >> "$vals"
  unset key
  write_vault_from "$vals"; rm -f "$vals"
  echo "KEY_STATUS=ADDED"
  echo "KEY_COUNT=$(vault_values | wc -l | tr -d ' ')"
}

key_status() {
  count=$(vault_values | wc -l | tr -d ' '); case "$count" in ''|*[!0-9]*) count=0;; esac
  slot=$(cat "$GEMINI_SLOT" 2>/dev/null); case "$slot" in ''|*[!0-9]*) slot=1;; esac
  [ "$count" -gt 0 ] || slot=0
  now=$(date +%s)
  echo "KEY_CONFIGURED=$([ "$count" -gt 0 ] && echo YES || echo NO)"
  echo "KEY_COUNT=$count"
  echo "ACTIVE_SLOT=$slot"
  i=1
  while [ "$i" -le 4 ]; do
    if [ "$i" -gt "$count" ]; then
      echo "KEY_${i}_STATUS=EMPTY"
    else
      until=$(kv "KEY_${i}_UNTIL" "$GEMINI_COOLDOWN"); case "$until" in ''|*[!0-9]*) until=0;; esac
      if [ "$until" -gt "$now" ] 2>/dev/null; then
        echo "KEY_${i}_STATUS=COOLDOWN"
        echo "KEY_${i}_COOLDOWN_UNTIL=$until"
      elif [ "$i" = "$slot" ]; then
        echo "KEY_${i}_STATUS=ACTIVE_READY"
      else
        echo "KEY_${i}_STATUS=READY"
      fi
    fi
    i=$((i+1))
  done
  echo "SECRET_VALUES=HIDDEN"
}

credential_status() {
  count=$(vault_values | wc -l | tr -d ' '); case "$count" in ''|*[!0-9]*) count=0;; esac
  now=$(date +%s); ready=0; cooldown=0
  i=1
  while [ "$i" -le "$count" ]; do
    until=$(kv "KEY_${i}_UNTIL" "$GEMINI_COOLDOWN"); case "$until" in ''|*[!0-9]*) until=0;; esac
    if [ "$until" -gt "$now" ] 2>/dev/null; then cooldown=$((cooldown+1)); else ready=$((ready+1)); fi
    i=$((i+1))
  done
  hermes="$CONFIG/hermes_cloud.env"
  ha=$(kv HERMES_ACCESS_KEY "$hermes")
  he=$(kv HERMES_ENDPOINT "$hermes")
  hi=$(kv HERMES_CLOUD_ID "$hermes")
  echo "GEMINI_KEY_COUNT=$count"
  echo "GEMINI_READY_COUNT=$ready"
  echo "GEMINI_COOLDOWN_COUNT=$cooldown"
  echo "HERMES_ACCESS_KEY_PRESENT=$([ -n "$ha" ] && echo YES || echo NO)"
  echo "HERMES_ENDPOINT_PRESENT=$([ -n "$he" ] && echo YES || echo NO)"
  echo "HERMES_CLOUD_ID_PRESENT=$([ -n "$hi" ] && echo YES || echo NO)"
  echo "SECRET_VALUES=HIDDEN"
  unset ha
}

sync_request() {
  apk="$1"; schema="$2"; req="$3"
  case "$apk" in ''|*[!0-9]*) echo "SYNC_STATUS=REJECTED"; echo "REASON=INVALID_APK_VERSION"; return 2;; esac
  [ "$schema" = "DJAEGER_AI_ADAPTIVE_V3" ] || { echo "SYNC_STATUS=REJECTED"; echo "REASON=SCHEMA_MISMATCH"; return 2; }
  req=$(printf '%s' "$req" | tr -cd 'A-Za-z0-9._:-' | cut -c1-96)
  [ -n "$req" ] || { echo "SYNC_STATUS=REJECTED"; echo "REASON=INVALID_REQUEST_ID"; return 2; }
  module_code=$(sed -n 's/^versionCode=//p' "$MODDIR/module.prop" 2>/dev/null | head -n1)
  [ -n "$module_code" ] || module_code=0
  expected_apk=111
  pair=NO; [ "$apk" = "$expected_apk" ] && [ "$module_code" = 210 ] && pair=YES
  now=$(date +%s)
  tmp="$(mktemp "${HANDSHAKE}.tmp.XXXXXX" 2>/dev/null)"; [ -n "$tmp" ] || tmp="${HANDSHAKE}.tmp.${now}"
  {
    echo "APK_VERSION_CODE=$apk"
    echo "EXPECTED_APK_VERSION_CODE=$expected_apk"
    echo "MODULE_VERSION_CODE=$module_code"
    echo "SCHEMA=$schema"
    echo "REQUEST_ID=$req"
    echo "ACK_ID=$req"
    echo "PAIR_VERIFIED=$pair"
    echo "ACK_AT=$now"
  } > "$tmp"
  chmod 600 "$tmp"; mv -f "$tmp" "$HANDSHAKE"
  if [ -r "$MODDIR/bin/publisher.sh" ]; then
    . "$MODDIR/bin/publisher.sh"
    publish_cc "$ROOT"
  fi
  gen=$(cat "$RUNTIME/snapshot_generation" 2>/dev/null | head -n1)
  echo "SYNC_STATUS=$([ "$pair" = YES ] && echo VERIFIED || echo VERSION_MISMATCH)"
  echo "PAIR_VERIFIED=$pair"
  echo "ACK_ID=$req"
  echo "SNAPSHOT_GENERATION=${gen:-0}"
}

select_key() {
  slot="$1"; count=$(vault_values | wc -l | tr -d ' ')
  case "$slot:$count" in *[!0-9:]*) echo "KEY_SELECT_REJECTED=INDEX"; return 2;; esac
  [ "$slot" -ge 1 ] && [ "$slot" -le "$count" ] || { echo "KEY_SELECT_REJECTED=RANGE"; return 2; }
  echo "$slot" > "$GEMINI_SLOT"; chmod 600 "$GEMINI_SLOT"
  echo "KEY_STATUS=SELECTED"
  echo "ACTIVE_SLOT=$slot"
}

remove_key() {
  slot="$1"; vals="$RUNTIME/.vault_values.$$"; kept="$RUNTIME/.vault_kept.$$"
  case "$slot" in ''|*[!0-9]*) echo "KEY_REMOVE_REJECTED=INDEX"; return 2;; esac
  vault_values > "$vals"; count=$(wc -l < "$vals" 2>/dev/null)
  [ "$slot" -ge 1 ] && [ "$slot" -le "$count" ] 2>/dev/null || { rm -f "$vals"; echo "KEY_REMOVE_REJECTED=RANGE"; return 2; }
  awk -v n="$slot" 'NR!=n' "$vals" > "$kept"
  write_vault_from "$kept"; rm -f "$vals" "$kept"
  echo "KEY_STATUS=REMOVED"
  echo "KEY_COUNT=$(vault_values | wc -l | tr -d ' ')"
}

registry_list() {
  kind="$1"
  if [ "$kind" = game ]; then
    echo "BUILTIN|sts.al|Arcane Legends"
    cat "$GAME_REGISTRY" 2>/dev/null
  else
    cat "$APP_REGISTRY" 2>/dev/null
  fi
}

registry_remove_exact() {
  _rr_file="$1"; _rr_pkg="$2"; _rr_tmp="$_rr_file.tmp.$$"
  awk -F'|' -v p="$_rr_pkg" '$2!=p' "$_rr_file" 2>/dev/null > "$_rr_tmp"
  chmod 600 "$_rr_tmp"; mv -f "$_rr_tmp" "$_rr_file"
}

registry_add() {
  kind="$1"
  IFS= read -r pkg || true
  IFS= read -r name || true
  pkg=$(printf '%s' "$pkg" | tr -d '\r\n ')
  name=$(clean_field "$name")
  valid_package "$pkg" || { echo "STATUS=REJECTED"; echo "REASON=INVALID_PACKAGE"; return 2; }
  [ -n "$name" ] || { echo "STATUS=REJECTED"; echo "REASON=EMPTY_NAME"; return 2; }
  if [ "$kind" = app ] && [ "$pkg" = sts.al ]; then
    echo "STATUS=REJECTED"; echo "REASON=BUILTIN_GAME"; return 2
  fi
  if [ "$kind" = game ]; then file="$GAME_REGISTRY"; other="$APP_REGISTRY"
  else file="$APP_REGISTRY"; other="$GAME_REGISTRY"
  fi
  registry_remove_exact "$file" "$pkg"
  registry_remove_exact "$other" "$pkg"
  printf 'MANUAL|%s|%s\n' "$pkg" "$name" >> "$file"
  chmod 600 "$file"
  echo "STATUS=ADDED"
  echo "PACKAGE=$pkg"
  echo "REGISTRY=$(printf '%s' "$kind" | tr 'a-z' 'A-Z')"
}

registry_remove() {
  kind="$1"
  IFS= read -r pkg || true
  pkg=$(printf '%s' "$pkg" | tr -d '\r\n ')
  valid_package "$pkg" || { echo "STATUS=REJECTED"; echo "REASON=INVALID_PACKAGE"; return 2; }
  [ "$kind" != game ] || [ "$pkg" != sts.al ] || { echo "STATUS=REJECTED"; echo "REASON=BUILTIN_GAME"; return 2; }
  [ "$kind" = game ] && file="$GAME_REGISTRY" || file="$APP_REGISTRY"
  registry_remove_exact "$file" "$pkg"
  echo "STATUS=REMOVED"
  echo "PACKAGE=$pkg"
}

record_feedback() {
  level="$1"
  case "$level" in very-comfortable|comfortable|less-comfortable|uncomfortable) :;; *) echo "FEEDBACK_REJECTED=INVALID_LEVEL"; return 2;; esac
  file="$HISTORY/comfort_feedback.csv"
  [ -f "$file" ] || echo "epoch,level,package,skin_c,battery_c,power_mw" > "$file"
  snap="$RUNTIME/snapshot.env"
  printf '%s,%s,%s,%s,%s,%s\n' "$(date +%s)" "$level" "$(clean_field "$(kv ACTIVE_PACKAGE "$snap")")" "$(clean_field "$(kv SKIN_TEMP_C "$snap")")" "$(clean_field "$(kv BATTERY_TEMP_C "$snap")")" "$(clean_field "$(kv POWER_MW "$snap")")" >> "$file"
  chmod 600 "$file"
  echo "COMFORT_FEEDBACK_RECORDED=$level"
  echo "POLICY_EFFECT=EVIDENCE_ONLY"
}

case "$1" in
  feedback) record_feedback "$2" ;;
  gemini-key-status|gemini-key-vault-status) key_status ;;
  credential-status) credential_status ;;
  sync-request) sync_request "$2" "$3" "$4" ;;
  gemini-key-stdin|gemini-key-add-stdin) add_key ;;
  gemini-key-select) select_key "$2" ;;
  gemini-key-remove) remove_key "$2" ;;
  gemini-key-delete)
    rm -f "$GEMINI_VAULT" "$GEMINI_SLOT"
    echo "KEY_STATUS=DELETED"; echo "KEY_COUNT=0" ;;
  gemini-chat-stdin)
    IFS= read -r _discard || true
    echo "CHAT_UNAVAILABLE=OBSERVER_VALIDATION_BUILD"; echo "REASON=NO_INTERACTIVE_CLOUD_CHAT_IN_BACKGROUND_MODULE"; exit 2 ;;
  gemini-chat-clear) echo "GEMINI_CHAT_HISTORY=NO_STORED_HISTORY" ;;
  gemini-knowledge-status)
    key_status
    echo "REASONER_STATE=$(kv GEMINI_STATE "$RUNTIME/gemini_reasoner.env")"
    echo "LEARNING_STATE=$(kv STATE "$HISTORY/learned_envelope.env")" ;;
  hermes-chat-stdin)
    IFS= read -r _discard || true
    echo "HERMES_CHAT_UNAVAILABLE=OBSERVER_VALIDATION_BUILD"; echo "REASON=HERMES_CLOUD_IS_CANDIDATE_REVIEW_ONLY"; exit 2 ;;
  hermes-chat-clear) echo "HERMES_CHAT_HISTORY=NO_STORED_HISTORY" ;;
  authority-status)
    _es="$(kv EXECUTOR_STATE "$RUNTIME/execution.env")"; [ -n "$_es" ] || _es=IDLE
    echo "AUTHORITY=LOCAL_VALIDATED_EXECUTOR"
    echo "OBSERVER=READ_ONLY"
    echo "CLOUD_HARDWARE_AUTHORITY=NONE"
    echo "SYSFS_WRITES=EXECUTOR_ONLY"
    echo "EXECUTOR=$_es" ;;
  kernel-status)
    snap="$RUNTIME/snapshot.env"
    lp="$(kv LITTLE_POLICY_PATH "$snap")"; bp="$(kv BIG_POLICY_PATH "$snap")"; gp="$(kv GPU_DEVFREQ_PATH "$snap")"
    echo "CAPABILITY=OBSERVE_AND_GATED_EXECUTE"
    echo "LITTLE_POLICY=$([ -n "$lp" ] && echo DETECTED || echo UNAVAILABLE)"
    echo "BIG_POLICY=$([ -n "$bp" ] && echo DETECTED || echo UNAVAILABLE)"
    echo "GPU_DEVFREQ=$([ -n "$gp" ] && echo DETECTED || echo UNAVAILABLE)"
    _a=0
    [ -n "$lp" ] && [ -w "$lp/scaling_min_freq" ] && [ -w "$lp/scaling_max_freq" ] && _a=$((_a+2))
    [ -n "$bp" ] && [ -w "$bp/scaling_min_freq" ] && [ -w "$bp/scaling_max_freq" ] && _a=$((_a+2))
    [ -n "$gp" ] && [ -w "$gp/min_freq" ] && [ -w "$gp/max_freq" ] && _a=$((_a+2))
    echo "WRITABLE_ACTUATORS=$_a" ;;
  maturity-audit)
    learn="$HISTORY/learned_envelope.env"; shadow="$RUNTIME/shadow.env"; exec="$RUNTIME/execution.env"
    echo "PACKAGE=$(kv PACKAGE "$learn")"
    echo "LEARNING_STATE=$(kv STATE "$learn")"
    echo "SAMPLES=$(kv SAMPLES "$learn")"
    echo "FRAME_WINDOWS=$(kv FRAME_WINDOWS "$learn")"
    echo "CONFIDENCE=$(kv CONFIDENCE "$learn")"
    echo "SHADOW_STATE=$(kv SHADOW_STATE "$shadow")"
    echo "EXECUTION_MODE=$(cat "$CONFIG/execution_mode" 2>/dev/null)"
    echo "EXECUTOR_STATE=$(kv EXECUTOR_STATE "$exec")" ;;
  execution-status)
    echo "EXECUTION_MODE=$(cat "$CONFIG/execution_mode" 2>/dev/null)"
    [ -r "$RUNTIME/execution.env" ] && cat "$RUNTIME/execution.env" || echo "EXECUTOR_STATE=IDLE" ;;
  execution-auto)
    echo AUTO > "$CONFIG/execution_mode"; chmod 600 "$CONFIG/execution_mode"
    echo "EXECUTION_MODE=AUTO" ;;
  execution-off)
    echo OFF > "$CONFIG/execution_mode"; chmod 600 "$CONFIG/execution_mode"
    rm -f "$ROOT/policy/approved.env"
    sh "$ROOT/../modules/djaeger_ai_observer/bin/executor.sh" "$ROOT" once >/dev/null 2>&1 || true
    echo "EXECUTION_MODE=OFF" ;;
  migration-status)
    if [ -r "$RECOVERY/migration.env" ]; then cat "$RECOVERY/migration.env"; else echo "MIGRATION_STATE=UNAVAILABLE"; fi ;;
  snapshot-status)
    snap="$ROOT/cc_snapshot"
    if [ -r "$snap" ]; then
      echo "SNAPSHOT=AVAILABLE"
      echo "CONTRACT=$(sed -n '/^__CONTROL_CENTER_SYNC__$/,/^__/s/^CONTRACT=//p' "$snap" | head -n1)"
      echo "UPDATED_AT=$(sed -n '/^__RUNTIME__$/,/^__/s/^UPDATED_AT=//p' "$snap" | head -n1)"
      echo "SNAPSHOT_GENERATION=$(sed -n '/^__CONTROL_CENTER_SYNC__$/,/^__/s/^SNAPSHOT_GENERATION=//p' "$snap" | head -n1)"
      echo "PAIR_VERIFIED=$(sed -n '/^__CONTROL_CENTER_SYNC__$/,/^__/s/^PAIR_VERIFIED=//p' "$snap" | head -n1)"
      echo "HANDSHAKE_ACK_ID=$(sed -n '/^__CONTROL_CENTER_SYNC__$/,/^__/s/^HANDSHAKE_ACK_ID=//p' "$snap" | head -n1)"
      echo "ATOMIC_PUBLISH=YES"
    else echo "SNAPSHOT=UNAVAILABLE"; exit 2; fi ;;
  game-registry-list) registry_list game ;;
  game-registry-add-stdin) registry_add game ;;
  game-registry-remove-stdin) registry_remove game ;;
  app-registry-list) registry_list app ;;
  app-registry-add-stdin) registry_add app ;;
  app-registry-remove-stdin) registry_remove app ;;
  *) echo "OBSERVERCTL_ERROR=UNKNOWN_COMMAND"; exit 2 ;;
esac
