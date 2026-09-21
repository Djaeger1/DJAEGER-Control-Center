#!/system/bin/sh

# Small, typed bridge used by the Observer APK. This bridge owns only
# DJAEGER Observer files. It cannot invoke a hardware executor or write sysfs.

ROOT=${DJAEGER_OBSERVER_ROOT:-/data/adb/djaeger_observer}
CONFIG="$ROOT/config"
RUNTIME="$ROOT/runtime"
HISTORY="$ROOT/history"
RECOVERY="$ROOT/recovery"
GEMINI_VAULT="$CONFIG/gemini_vault.env"
GEMINI_SLOT="$CONFIG/gemini_slot"
GAME_REGISTRY="$CONFIG/game_registry.tsv"
APP_REGISTRY="$CONFIG/app_registry.tsv"

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
  echo "KEY_CONFIGURED=$([ "$count" -gt 0 ] && echo YES || echo NO)"
  echo "KEY_COUNT=$count"
  echo "ACTIVE_SLOT=$slot"
  echo "SECRET_VALUES=HIDDEN"
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
    echo "AUTHORITY=STOCK_KERNEL"
    echo "OBSERVER=READ_ONLY"
    echo "SYSFS_WRITES=DISABLED"
    echo "EXECUTOR=NOT_PACKAGED" ;;
  kernel-status)
    snap="$RUNTIME/snapshot.env"
    echo "CAPABILITY=READ_ONLY_TELEMETRY"
    echo "LITTLE_POLICY=$([ -n "$(kv LITTLE_POLICY_PATH "$snap")" ] && echo DETECTED || echo UNAVAILABLE)"
    echo "BIG_POLICY=$([ -n "$(kv BIG_POLICY_PATH "$snap")" ] && echo DETECTED || echo UNAVAILABLE)"
    echo "GPU_DEVFREQ=$([ -n "$(kv GPU_DEVFREQ_PATH "$snap")" ] && echo DETECTED || echo UNAVAILABLE)"
    echo "WRITABLE_ACTUATORS=0" ;;
  maturity-audit)
    learn="$HISTORY/learned_envelope.env"; shadow="$RUNTIME/shadow.env"
    echo "PACKAGE=$(kv PACKAGE "$learn")"
    echo "LEARNING_STATE=$(kv STATE "$learn")"
    echo "SAMPLES=$(kv SAMPLES "$learn")"
    echo "FRAME_WINDOWS=$(kv FRAME_WINDOWS "$learn")"
    echo "CONFIDENCE=$(kv CONFIDENCE "$learn")"
    echo "SHADOW_STATE=$(kv SHADOW_STATE "$shadow")"
    echo "EXECUTOR_ENABLED=0" ;;
  migration-status)
    if [ -r "$RECOVERY/migration.env" ]; then cat "$RECOVERY/migration.env"; else echo "MIGRATION_STATE=UNAVAILABLE"; fi ;;
  snapshot-status)
    snap="$ROOT/cc_snapshot"
    if [ -r "$snap" ]; then
      echo "SNAPSHOT=AVAILABLE"
      echo "CONTRACT=$(sed -n '/^__CONTROL_CENTER_SYNC__$/,/^__/s/^CONTRACT=//p' "$snap" | head -n1)"
      echo "UPDATED_AT=$(sed -n '/^__RUNTIME__$/,/^__/s/^UPDATED_AT=//p' "$snap" | head -n1)"
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
