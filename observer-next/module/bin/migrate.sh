#!/system/bin/sh
# DJAEGER AI clean credential migration.
# Only explicitly named DJAEGER AI credentials/identity fields are imported.
ROOT="$1"
LEGACY=${DJAEGER_LEGACY_ROOT:-/data/adb/djaeger_ai}
LEGACY_MODULE=${DJAEGER_LEGACY_MODULE_ROOT:-/data/adb/modules/djaeger_game_stabilizer}
LEGACY_EXTRA="/data/adb/djaeger /data/adb/modules/djaeger_ai /data/adb/modules/djaeger_game_stabilizer"
MARK="$ROOT/recovery/migration.env"
CONFIG="$ROOT/config"
GEMINI="$CONFIG/gemini_vault.env"
HERMES="$CONFIG/hermes_cloud.env"
IDENTITY="$CONFIG/identity.env"
RAILWAY="$CONFIG/railway.env"
GEMINI_SLOT="$CONFIG/gemini_slot"
GEMINI_COOLDOWN="$CONFIG/gemini_cooldown.env"
NEURON="$CONFIG/hermes_neuron_legacy.env"

mkdir -p "$ROOT/recovery" "$ROOT/runtime" "$CONFIG"
chmod 700 "$ROOT/recovery" "$CONFIG" 2>/dev/null

forbidden_path(){
  _p="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  _a=djaeger; _b=work; _c=hermes
  printf '%s' "$_p" | grep -Eq "${_a}[-_ ]?${_b}|${_c}[-_ ]?${_b}|/(studio|youtube|publisher|renderer)(/|[._-])"
}
safe_value(){ printf '%s' "$1" | tr -d '\r\n' | cut -c1-1024; }
extract_exact(){
  _key="$1"; _file="$2"
  sed -n "s/^[[:space:]]*$_key[[:space:]]*=[[:space:]]*['\"]\{0,1\}\([^'\"[:space:]]\{1,1024\}\).*/\1/p" "$_file" 2>/dev/null | head -n1
}
valid_gemini_key(){
  _v="$1"; _n="$(printf '%s' "$_v" | wc -c | tr -d ' ')"
  case "$_n" in ''|*[!0-9]*) return 1;; esac
  [ "$_n" -ge 20 ] && [ "$_n" -le 256 ] || return 1
  printf '%s' "$_v" | grep -Eq '^[A-Za-z0-9._-]+

STATE=NO_LEGACY
LEGACY_PRESENT=NO
TMP_KEYS="$ROOT/runtime/.migrate_gemini.$$"
TMP_SOURCES="$ROOT/runtime/.migration_sources.$$"
: > "$TMP_KEYS"
sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | while IFS= read -r _k; do valid_gemini_key "$_k" && printf '%s\n' "$_k"; done >> "$TMP_KEYS"
if [ -r "$LEGACY/gemini_keys.vault" ]; then
  while IFS= read -r _k; do
    _k="$(printf '%s' "$_k" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    valid_gemini_key "$_k" && printf '%s\n' "$_k"
  done < "$LEGACY/gemini_keys.vault" >> "$TMP_KEYS"
fi
LEGACY_ACTIVE_KEY="$(extract_exact GEMINI_API_KEY "$LEGACY/gemini.conf")"
valid_gemini_key "$LEGACY_ACTIVE_KEY" && printf '%s\n' "$LEGACY_ACTIVE_KEY" >> "$TMP_KEYS"

H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$HERMES")"
H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$HERMES")"
H_ID="$(extract_exact HERMES_CLOUD_ID "$HERMES")"
DEVICE_ID="$(extract_exact DEVICE_ID "$IDENTITY")"
R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$RAILWAY")"
R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$RAILWAY")"
G_MODEL="$(extract_exact GEMINI_MODEL "$CONFIG/gemini.env")"

# Legacy REMOTEBOOT1 used ACCESS_TOKEN + ENDPOINT. Import those aliases only
# from exact DJAEGER Railway config locations; never from arbitrary files.
for _rf in "$LEGACY/railway.conf" "$LEGACY_MODULE/system/etc/djaeger/railway/railway.conf"; do
  [ -r "$_rf" ] || continue
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$_rf")"
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact ACCESS_TOKEN "$_rf")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$_rf")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact ENDPOINT "$_rf")"
done

STATE=NO_LEGACY
: > "$TMP_SOURCES"
for _root in "$LEGACY" "$LEGACY_MODULE" $LEGACY_EXTRA; do
  [ -d "$_root" ] || continue
  STATE=LEGACY_FOUND
  LEGACY_PRESENT=YES
  find "$_root" -maxdepth 7 -type f -size -256k 2>/dev/null | while IFS= read -r f; do
    forbidden_path "$f" && continue
    printf '%s\n' "$f"
  done >> "$TMP_SOURCES"
done

while IFS= read -r f; do
  [ -r "$f" ] || continue
  for k in GEMINI_API_KEY KEY_1 KEY_2 KEY_3 KEY_4; do
    v="$(extract_exact "$k" "$f")"; [ -n "$v" ] && printf '%s\n' "$(safe_value "$v")" >> "$TMP_KEYS"
  done
  [ -n "$G_MODEL" ] || G_MODEL="$(extract_exact GEMINI_MODEL "$f")"
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$f")"
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_SHARED_TOKEN "$f")"
  [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$f")"
  case "$H_ENDPOINT" in https://*) :;; *) _base="$(extract_exact ENDPOINT "$f")"; case "$_base" in https://*) H_ENDPOINT="$_base";; esac;; esac
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$f")"
  [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$f")"
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$f")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$f")"
done < "$TMP_SOURCES"
rm -f "$TMP_SOURCES"

for f in   "$LEGACY/HERMES_CLOUD_CREDENTIALS.txt"   /data/user/0/com.termoneplus/app_HOME/hermes-cloud-deploy/hermes-cloud-djaeger/HERMES_CLOUD_CREDENTIALS.txt   /data/media/0/Download/HERMES_CLOUD_CREDENTIALS.txt   /sdcard/Download/HERMES_CLOUD_CREDENTIALS.txt; do
  [ -r "$f" ] || continue
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$f")"
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_SHARED_TOKEN "$f")"
  _hep="$(extract_exact HERMES_ENDPOINT "$f")"
  case "$_hep" in
    https://*) [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$_hep" ;;
    /*) H_PATH="$_hep" ;;
  esac
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$f")"
  [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$f")"
  break
done

# Normalize legacy Hermes base ENDPOINT + relative HERMES_ENDPOINT path.
if [ -r "$LEGACY/hermes_cloud.conf" ]; then
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$LEGACY/hermes_cloud.conf")"
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_SHARED_TOKEN "$LEGACY/hermes_cloud.conf")"
  H_BASE="$(extract_exact ENDPOINT "$LEGACY/hermes_cloud.conf")"
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$LEGACY/hermes_cloud.conf")"
  case "$H_ENDPOINT" in https://*) :;; *)
    case "$H_BASE" in https://*)
      H_BASE="$(printf '%s' "$H_BASE" | sed 's:/*$::')"
      case "$H_PATH" in /*) H_ENDPOINT="$H_BASE$H_PATH";; *) H_ENDPOINT="$H_BASE";; esac
    ;; esac
  ;; esac
fi

awk 'NF && !seen[$0]++ {n++; if(n<=4) print "KEY_" n "=" $0}' "$TMP_KEYS" > "$GEMINI.tmp.$"
rm -f "$TMP_KEYS"
if [ -s "$GEMINI.tmp.$" ]; then chmod 600 "$GEMINI.tmp.$"; mv -f "$GEMINI.tmp.$" "$GEMINI"; else rm -f "$GEMINI.tmp.$"; fi

# Restore selected Gemini slot and per-key cooldowns without exposing key values.
if [ -n "$LEGACY_ACTIVE_KEY" ]; then
  _slot="$(awk -F= -v k="$LEGACY_ACTIVE_KEY" '$2==k{sub(/^KEY_/,"",$1);print $1;exit}' "$GEMINI" 2>/dev/null)"
  case "$_slot" in 1|2|3|4) printf '%s\n' "$_slot" > "$GEMINI_SLOT"; chmod 600 "$GEMINI_SLOT";; esac
fi
if [ -r "$LEGACY/gemini_key_cooldowns" ]; then
  grep -E '^KEY_[1-4]_UNTIL=[0-9]+ printf 'GEMINI_MODEL=%s\n' "$(safe_value "$G_MODEL")" > "$CONFIG/gemini.env.tmp.$$"; chmod 600 "$CONFIG/gemini.env.tmp.$$"; mv -f "$CONFIG/gemini.env.tmp.$$" "$CONFIG/gemini.env"; fi

{
  [ -n "$H_ACCESS" ] && printf 'HERMES_ACCESS_KEY=%s\n' "$(safe_value "$H_ACCESS")"
  [ -n "$H_ENDPOINT" ] && printf 'HERMES_ENDPOINT=%s\n' "$(safe_value "$H_ENDPOINT")"
  [ -n "$H_ID" ] && printf 'HERMES_CLOUD_ID=%s\n' "$(safe_value "$H_ID")"
} > "$HERMES.tmp.$$"
if [ -s "$HERMES.tmp.$$" ]; then chmod 600 "$HERMES.tmp.$$"; mv -f "$HERMES.tmp.$$" "$HERMES"; else rm -f "$HERMES.tmp.$$"; fi

if [ -n "$DEVICE_ID" ]; then printf 'DEVICE_ID=%s\n' "$(safe_value "$DEVICE_ID")" > "$IDENTITY.tmp.$$"; chmod 600 "$IDENTITY.tmp.$$"; mv -f "$IDENTITY.tmp.$$" "$IDENTITY"; fi
if [ -n "$R_TOKEN" ] || [ -n "$R_URL" ]; then
  {
    [ -n "$R_TOKEN" ] && printf 'DJAEGER_ACCESS_TOKEN=%s\n' "$(safe_value "$R_TOKEN")"
    [ -n "$R_URL" ] && printf 'DJAEGER_RAILWAY_URL=%s\n' "$(safe_value "$R_URL")"
  } > "$RAILWAY.tmp.$"
  chmod 600 "$RAILWAY.tmp.$"; mv -f "$RAILWAY.tmp.$" "$RAILWAY"
fi

# Preserve the old local Neuron estimate separately from provider/account quota.
NEURON_PRESENT=NO
if [ -r "$LEGACY/hermes/neuron_budget.env" ]; then
  N_USED="$(extract_exact USED_EST "$LEGACY/hermes/neuron_budget.env")"
  N_LIMIT="$(extract_exact LIMIT "$LEGACY/hermes/neuron_budget.env")"
  N_DAY="$(extract_exact EPOCH_DAY "$LEGACY/hermes/neuron_budget.env")"
  case "$N_USED:$N_LIMIT" in
    *[!0-9:]*|:*) : ;;
    *) {
      echo "SOURCE=LEGACY_LOCAL_ACCOUNTING"; echo "ESTIMATED=YES"
      echo "USED_EST=$N_USED"; echo "LIMIT=$N_LIMIT"
      case "$N_DAY" in ''|*[!0-9]*) :;; *) echo "EPOCH_DAY=$N_DAY";; esac
      echo "IMPORTED_AT=$(date +%s)"
    } > "$NEURON.tmp.$"; chmod 600 "$NEURON.tmp.$"; mv -f "$NEURON.tmp.$" "$NEURON"; NEURON_PRESENT=YES ;;
  esac
fi

GCOUNT=$(sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF{n++}END{print n+0}')
HCOUNT=0; [ -s "$HERMES" ] && HCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$HERMES")
ICOUNT=0; [ -s "$IDENTITY" ] && ICOUNT=1
RCOUNT=0; [ -s "$RAILWAY" ] && RCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$RAILWAY")
if [ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ] || [ "$RCOUNT" -gt 0 ]; then STATE=CLEAN_IMPORT_CREATED; else STATE=NO_CREDENTIALS_FOUND; fi

TMP="$MARK.tmp.$$"
{
  echo "MIGRATION_SCHEMA=7"
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_PATH=$LEGACY"
  echo "LEGACY_MODULE_PATH=$LEGACY_MODULE"
  echo "LEGACY_CONFIG_PRESENT=$LEGACY_PRESENT"
  echo "GEMINI_KEY_COUNT=$GCOUNT"
  echo "HERMES_FIELD_COUNT=$HCOUNT"
  echo "HERMES_ACCESS_KEY_PRESENT=$([ -n "$H_ACCESS" ] && echo YES || echo NO)"
  echo "HERMES_ENDPOINT_PRESENT=$([ -n "$H_ENDPOINT" ] && echo YES || echo NO)"
  echo "HERMES_CLOUD_ID_PRESENT=$([ -n "$H_ID" ] && echo YES || echo NO)"
  echo "NEURON_LOCAL_ESTIMATE_PRESENT=$NEURON_PRESENT"
  echo "IDENTITY_IMPORTED=$([ "$ICOUNT" -gt 0 ] && echo YES || echo NO)"
  echo "RAILWAY_TOKEN_IMPORTED=$([ -n "$R_TOKEN" ] && echo YES || echo NO)"
  echo "RAILWAY_URL_IMPORTED=$([ -n "$R_URL" ] && echo YES || echo NO)"
  echo "CREDENTIAL_FILE_COUNT=$((GCOUNT + HCOUNT + ICOUNT + RCOUNT))"
  echo "RAW_LEGACY_FILES_IMPORTED=0"
  echo "LEGACY_HARDWARE_CONTROLLER_IMPORTED=NO"
  echo "LEGACY_PROFILE_MAP_IMPORTED=NO"
  echo "FOREIGN_PROJECT_IMPORTS=0"
  echo "MIGRATION_POLICY=EXPLICIT_KEY_ALLOWLIST_ONLY"
  echo "MIGRATED_AT=$(date +%s)"
} > "$TMP"
chmod 600 "$TMP"; mv -f "$TMP" "$MARK"
chmod -R go-rwx "$ROOT/recovery" "$ROOT/config" 2>/dev/null

}

STATE=NO_LEGACY
LEGACY_PRESENT=NO
TMP_KEYS="$ROOT/runtime/.migrate_gemini.$$"
TMP_SOURCES="$ROOT/runtime/.migration_sources.$$"
: > "$TMP_KEYS"
sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF' >> "$TMP_KEYS"

H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$HERMES")"
H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$HERMES")"
H_ID="$(extract_exact HERMES_CLOUD_ID "$HERMES")"
DEVICE_ID="$(extract_exact DEVICE_ID "$IDENTITY")"
R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$RAILWAY")"
R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$RAILWAY")"
G_MODEL="$(extract_exact GEMINI_MODEL "$CONFIG/gemini.env")"

# Legacy REMOTEBOOT1 used ACCESS_TOKEN + ENDPOINT. Import those aliases only
# from exact DJAEGER Railway config locations; never from arbitrary files.
for _rf in "$LEGACY/railway.conf" "$LEGACY_MODULE/system/etc/djaeger/railway/railway.conf"; do
  [ -r "$_rf" ] || continue
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$_rf")"
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact ACCESS_TOKEN "$_rf")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$_rf")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact ENDPOINT "$_rf")"
done

STATE=NO_LEGACY
: > "$TMP_SOURCES"
for _root in "$LEGACY" "$LEGACY_MODULE" $LEGACY_EXTRA; do
  [ -d "$_root" ] || continue
  STATE=LEGACY_FOUND
  LEGACY_PRESENT=YES
  find "$_root" -maxdepth 7 -type f -size -256k 2>/dev/null | while IFS= read -r f; do
    forbidden_path "$f" && continue
    printf '%s\n' "$f"
  done >> "$TMP_SOURCES"
done

while IFS= read -r f; do
  [ -r "$f" ] || continue
  for k in GEMINI_API_KEY KEY_1 KEY_2 KEY_3 KEY_4; do
    v="$(extract_exact "$k" "$f")"; [ -n "$v" ] && printf '%s\n' "$(safe_value "$v")" >> "$TMP_KEYS"
  done
  [ -n "$G_MODEL" ] || G_MODEL="$(extract_exact GEMINI_MODEL "$f")"
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$f")"
  [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$f")"
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$f")"
  [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$f")"
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$f")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$f")"
done < "$TMP_SOURCES"
rm -f "$TMP_SOURCES"

for f in   /data/user/0/com.termoneplus/app_HOME/hermes-cloud-deploy/hermes-cloud-djaeger/HERMES_CLOUD_CREDENTIALS.txt   /data/media/0/Download/HERMES_CLOUD_CREDENTIALS.txt   /sdcard/Download/HERMES_CLOUD_CREDENTIALS.txt; do
  [ -r "$f" ] || continue
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$f")"
  [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$f")"
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$f")"
  [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$f")"
  break
done

awk 'NF && !seen[$0]++ {n++; if(n<=4) print "KEY_" n "=" $0}' "$TMP_KEYS" > "$GEMINI.tmp.$$"
rm -f "$TMP_KEYS"
if [ -s "$GEMINI.tmp.$$" ]; then chmod 600 "$GEMINI.tmp.$$"; mv -f "$GEMINI.tmp.$$" "$GEMINI"; else rm -f "$GEMINI.tmp.$$"; fi

if [ -n "$G_MODEL" ]; then printf 'GEMINI_MODEL=%s\n' "$(safe_value "$G_MODEL")" > "$CONFIG/gemini.env.tmp.$$"; chmod 600 "$CONFIG/gemini.env.tmp.$$"; mv -f "$CONFIG/gemini.env.tmp.$$" "$CONFIG/gemini.env"; fi

{
  [ -n "$H_ACCESS" ] && printf 'HERMES_ACCESS_KEY=%s\n' "$(safe_value "$H_ACCESS")"
  [ -n "$H_ENDPOINT" ] && printf 'HERMES_ENDPOINT=%s\n' "$(safe_value "$H_ENDPOINT")"
  [ -n "$H_ID" ] && printf 'HERMES_CLOUD_ID=%s\n' "$(safe_value "$H_ID")"
} > "$HERMES.tmp.$$"
if [ -s "$HERMES.tmp.$$" ]; then chmod 600 "$HERMES.tmp.$$"; mv -f "$HERMES.tmp.$$" "$HERMES"; else rm -f "$HERMES.tmp.$$"; fi

if [ -n "$DEVICE_ID" ]; then printf 'DEVICE_ID=%s\n' "$(safe_value "$DEVICE_ID")" > "$IDENTITY.tmp.$$"; chmod 600 "$IDENTITY.tmp.$$"; mv -f "$IDENTITY.tmp.$$" "$IDENTITY"; fi
if [ -n "$R_TOKEN" ] || [ -n "$R_URL" ]; then
  {
    [ -n "$R_TOKEN" ] && printf 'DJAEGER_ACCESS_TOKEN=%s\n' "$(safe_value "$R_TOKEN")"
    [ -n "$R_URL" ] && printf 'DJAEGER_RAILWAY_URL=%s\n' "$(safe_value "$R_URL")"
  } > "$RAILWAY.tmp.$"
  chmod 600 "$RAILWAY.tmp.$"; mv -f "$RAILWAY.tmp.$" "$RAILWAY"
fi

GCOUNT=$(sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF{n++}END{print n+0}')
HCOUNT=0; [ -s "$HERMES" ] && HCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$HERMES")
ICOUNT=0; [ -s "$IDENTITY" ] && ICOUNT=1
RCOUNT=0; [ -s "$RAILWAY" ] && RCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$RAILWAY")
if [ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ] || [ "$RCOUNT" -gt 0 ]; then STATE=CLEAN_IMPORT_CREATED; else STATE=NO_CREDENTIALS_FOUND; fi

TMP="$MARK.tmp.$$"
{
  echo "MIGRATION_SCHEMA=6"
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_PATH=$LEGACY"
  echo "LEGACY_MODULE_PATH=$LEGACY_MODULE"
  echo "LEGACY_CONFIG_PRESENT=$LEGACY_PRESENT"
  echo "GEMINI_KEY_COUNT=$GCOUNT"
  echo "HERMES_FIELD_COUNT=$HCOUNT"
  echo "IDENTITY_IMPORTED=$([ "$ICOUNT" -gt 0 ] && echo YES || echo NO)"
  echo "RAILWAY_TOKEN_IMPORTED=$([ -n "$R_TOKEN" ] && echo YES || echo NO)"
  echo "RAILWAY_URL_IMPORTED=$([ -n "$R_URL" ] && echo YES || echo NO)"
  echo "CREDENTIAL_FILE_COUNT=$((GCOUNT + HCOUNT + ICOUNT + RCOUNT))"
  echo "RAW_LEGACY_FILES_IMPORTED=0"
  echo "LEGACY_HARDWARE_CONTROLLER_IMPORTED=NO"
  echo "LEGACY_PROFILE_MAP_IMPORTED=NO"
  echo "FOREIGN_PROJECT_IMPORTS=0"
  echo "MIGRATION_POLICY=EXPLICIT_KEY_ALLOWLIST_ONLY"
  echo "MIGRATED_AT=$(date +%s)"
} > "$TMP"
chmod 600 "$TMP"; mv -f "$TMP" "$MARK"
chmod -R go-rwx "$ROOT/recovery" "$ROOT/config" 2>/dev/null
 "$GEMINI_COOLDOWN" 2>/dev/null > "$GEMINI_COOLDOWN.tmp.$" || :
  while IFS='|' read -r _slot _until _reason; do
    case "$_slot" in 1|2|3|4) :;; *) continue;; esac
    case "$_until" in ''|*[!0-9]*) continue;; esac
    grep -v "^KEY_$_slot""_UNTIL=" "$GEMINI_COOLDOWN.tmp.$" > "$GEMINI_COOLDOWN.tmp2.$" 2>/dev/null || :
    mv -f "$GEMINI_COOLDOWN.tmp2.$" "$GEMINI_COOLDOWN.tmp.$"
    echo "KEY_$_slot""_UNTIL=$_until" >> "$GEMINI_COOLDOWN.tmp.$"
  done < "$LEGACY/gemini_key_cooldowns"
  if [ -s "$GEMINI_COOLDOWN.tmp.$" ]; then chmod 600 "$GEMINI_COOLDOWN.tmp.$"; mv -f "$GEMINI_COOLDOWN.tmp.$" "$GEMINI_COOLDOWN"; else rm -f "$GEMINI_COOLDOWN.tmp.$"; fi
fi
unset LEGACY_ACTIVE_KEY

if [ -n "$G_MODEL" ]; then printf 'GEMINI_MODEL=%s\n' "$(safe_value "$G_MODEL")" > "$CONFIG/gemini.env.tmp.$$"; chmod 600 "$CONFIG/gemini.env.tmp.$$"; mv -f "$CONFIG/gemini.env.tmp.$$" "$CONFIG/gemini.env"; fi

{
  [ -n "$H_ACCESS" ] && printf 'HERMES_ACCESS_KEY=%s\n' "$(safe_value "$H_ACCESS")"
  [ -n "$H_ENDPOINT" ] && printf 'HERMES_ENDPOINT=%s\n' "$(safe_value "$H_ENDPOINT")"
  [ -n "$H_ID" ] && printf 'HERMES_CLOUD_ID=%s\n' "$(safe_value "$H_ID")"
} > "$HERMES.tmp.$$"
if [ -s "$HERMES.tmp.$$" ]; then chmod 600 "$HERMES.tmp.$$"; mv -f "$HERMES.tmp.$$" "$HERMES"; else rm -f "$HERMES.tmp.$$"; fi

if [ -n "$DEVICE_ID" ]; then printf 'DEVICE_ID=%s\n' "$(safe_value "$DEVICE_ID")" > "$IDENTITY.tmp.$$"; chmod 600 "$IDENTITY.tmp.$$"; mv -f "$IDENTITY.tmp.$$" "$IDENTITY"; fi
if [ -n "$R_TOKEN" ] || [ -n "$R_URL" ]; then
  {
    [ -n "$R_TOKEN" ] && printf 'DJAEGER_ACCESS_TOKEN=%s\n' "$(safe_value "$R_TOKEN")"
    [ -n "$R_URL" ] && printf 'DJAEGER_RAILWAY_URL=%s\n' "$(safe_value "$R_URL")"
  } > "$RAILWAY.tmp.$"
  chmod 600 "$RAILWAY.tmp.$"; mv -f "$RAILWAY.tmp.$" "$RAILWAY"
fi

GCOUNT=$(sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF{n++}END{print n+0}')
HCOUNT=0; [ -s "$HERMES" ] && HCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$HERMES")
ICOUNT=0; [ -s "$IDENTITY" ] && ICOUNT=1
RCOUNT=0; [ -s "$RAILWAY" ] && RCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$RAILWAY")
if [ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ] || [ "$RCOUNT" -gt 0 ]; then STATE=CLEAN_IMPORT_CREATED; else STATE=NO_CREDENTIALS_FOUND; fi

TMP="$MARK.tmp.$$"
{
  echo "MIGRATION_SCHEMA=6"
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_PATH=$LEGACY"
  echo "LEGACY_MODULE_PATH=$LEGACY_MODULE"
  echo "LEGACY_CONFIG_PRESENT=$LEGACY_PRESENT"
  echo "GEMINI_KEY_COUNT=$GCOUNT"
  echo "HERMES_FIELD_COUNT=$HCOUNT"
  echo "IDENTITY_IMPORTED=$([ "$ICOUNT" -gt 0 ] && echo YES || echo NO)"
  echo "RAILWAY_TOKEN_IMPORTED=$([ -n "$R_TOKEN" ] && echo YES || echo NO)"
  echo "RAILWAY_URL_IMPORTED=$([ -n "$R_URL" ] && echo YES || echo NO)"
  echo "CREDENTIAL_FILE_COUNT=$((GCOUNT + HCOUNT + ICOUNT + RCOUNT))"
  echo "RAW_LEGACY_FILES_IMPORTED=0"
  echo "LEGACY_HARDWARE_CONTROLLER_IMPORTED=NO"
  echo "LEGACY_PROFILE_MAP_IMPORTED=NO"
  echo "FOREIGN_PROJECT_IMPORTS=0"
  echo "MIGRATION_POLICY=EXPLICIT_KEY_ALLOWLIST_ONLY"
  echo "MIGRATED_AT=$(date +%s)"
} > "$TMP"
chmod 600 "$TMP"; mv -f "$TMP" "$MARK"
chmod -R go-rwx "$ROOT/recovery" "$ROOT/config" 2>/dev/null

}

STATE=NO_LEGACY
LEGACY_PRESENT=NO
TMP_KEYS="$ROOT/runtime/.migrate_gemini.$$"
TMP_SOURCES="$ROOT/runtime/.migration_sources.$$"
: > "$TMP_KEYS"
sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF' >> "$TMP_KEYS"

H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$HERMES")"
H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$HERMES")"
H_ID="$(extract_exact HERMES_CLOUD_ID "$HERMES")"
DEVICE_ID="$(extract_exact DEVICE_ID "$IDENTITY")"
R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$RAILWAY")"
R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$RAILWAY")"
G_MODEL="$(extract_exact GEMINI_MODEL "$CONFIG/gemini.env")"

# Legacy REMOTEBOOT1 used ACCESS_TOKEN + ENDPOINT. Import those aliases only
# from exact DJAEGER Railway config locations; never from arbitrary files.
for _rf in "$LEGACY/railway.conf" "$LEGACY_MODULE/system/etc/djaeger/railway/railway.conf"; do
  [ -r "$_rf" ] || continue
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$_rf")"
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact ACCESS_TOKEN "$_rf")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$_rf")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact ENDPOINT "$_rf")"
done

STATE=NO_LEGACY
: > "$TMP_SOURCES"
for _root in "$LEGACY" "$LEGACY_MODULE" $LEGACY_EXTRA; do
  [ -d "$_root" ] || continue
  STATE=LEGACY_FOUND
  LEGACY_PRESENT=YES
  find "$_root" -maxdepth 7 -type f -size -256k 2>/dev/null | while IFS= read -r f; do
    forbidden_path "$f" && continue
    printf '%s\n' "$f"
  done >> "$TMP_SOURCES"
done

while IFS= read -r f; do
  [ -r "$f" ] || continue
  for k in GEMINI_API_KEY KEY_1 KEY_2 KEY_3 KEY_4; do
    v="$(extract_exact "$k" "$f")"; [ -n "$v" ] && printf '%s\n' "$(safe_value "$v")" >> "$TMP_KEYS"
  done
  [ -n "$G_MODEL" ] || G_MODEL="$(extract_exact GEMINI_MODEL "$f")"
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$f")"
  [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$f")"
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$f")"
  [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$f")"
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$f")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$f")"
done < "$TMP_SOURCES"
rm -f "$TMP_SOURCES"

for f in   /data/user/0/com.termoneplus/app_HOME/hermes-cloud-deploy/hermes-cloud-djaeger/HERMES_CLOUD_CREDENTIALS.txt   /data/media/0/Download/HERMES_CLOUD_CREDENTIALS.txt   /sdcard/Download/HERMES_CLOUD_CREDENTIALS.txt; do
  [ -r "$f" ] || continue
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$f")"
  [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$f")"
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$f")"
  [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$f")"
  break
done

awk 'NF && !seen[$0]++ {n++; if(n<=4) print "KEY_" n "=" $0}' "$TMP_KEYS" > "$GEMINI.tmp.$$"
rm -f "$TMP_KEYS"
if [ -s "$GEMINI.tmp.$$" ]; then chmod 600 "$GEMINI.tmp.$$"; mv -f "$GEMINI.tmp.$$" "$GEMINI"; else rm -f "$GEMINI.tmp.$$"; fi

if [ -n "$G_MODEL" ]; then printf 'GEMINI_MODEL=%s\n' "$(safe_value "$G_MODEL")" > "$CONFIG/gemini.env.tmp.$$"; chmod 600 "$CONFIG/gemini.env.tmp.$$"; mv -f "$CONFIG/gemini.env.tmp.$$" "$CONFIG/gemini.env"; fi

{
  [ -n "$H_ACCESS" ] && printf 'HERMES_ACCESS_KEY=%s\n' "$(safe_value "$H_ACCESS")"
  [ -n "$H_ENDPOINT" ] && printf 'HERMES_ENDPOINT=%s\n' "$(safe_value "$H_ENDPOINT")"
  [ -n "$H_ID" ] && printf 'HERMES_CLOUD_ID=%s\n' "$(safe_value "$H_ID")"
} > "$HERMES.tmp.$$"
if [ -s "$HERMES.tmp.$$" ]; then chmod 600 "$HERMES.tmp.$$"; mv -f "$HERMES.tmp.$$" "$HERMES"; else rm -f "$HERMES.tmp.$$"; fi

if [ -n "$DEVICE_ID" ]; then printf 'DEVICE_ID=%s\n' "$(safe_value "$DEVICE_ID")" > "$IDENTITY.tmp.$$"; chmod 600 "$IDENTITY.tmp.$$"; mv -f "$IDENTITY.tmp.$$" "$IDENTITY"; fi
if [ -n "$R_TOKEN" ] || [ -n "$R_URL" ]; then
  {
    [ -n "$R_TOKEN" ] && printf 'DJAEGER_ACCESS_TOKEN=%s\n' "$(safe_value "$R_TOKEN")"
    [ -n "$R_URL" ] && printf 'DJAEGER_RAILWAY_URL=%s\n' "$(safe_value "$R_URL")"
  } > "$RAILWAY.tmp.$"
  chmod 600 "$RAILWAY.tmp.$"; mv -f "$RAILWAY.tmp.$" "$RAILWAY"
fi

GCOUNT=$(sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF{n++}END{print n+0}')
HCOUNT=0; [ -s "$HERMES" ] && HCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$HERMES")
ICOUNT=0; [ -s "$IDENTITY" ] && ICOUNT=1
RCOUNT=0; [ -s "$RAILWAY" ] && RCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$RAILWAY")
if [ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ] || [ "$RCOUNT" -gt 0 ]; then STATE=CLEAN_IMPORT_CREATED; else STATE=NO_CREDENTIALS_FOUND; fi

TMP="$MARK.tmp.$$"
{
  echo "MIGRATION_SCHEMA=6"
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_PATH=$LEGACY"
  echo "LEGACY_MODULE_PATH=$LEGACY_MODULE"
  echo "LEGACY_CONFIG_PRESENT=$LEGACY_PRESENT"
  echo "GEMINI_KEY_COUNT=$GCOUNT"
  echo "HERMES_FIELD_COUNT=$HCOUNT"
  echo "IDENTITY_IMPORTED=$([ "$ICOUNT" -gt 0 ] && echo YES || echo NO)"
  echo "RAILWAY_TOKEN_IMPORTED=$([ -n "$R_TOKEN" ] && echo YES || echo NO)"
  echo "RAILWAY_URL_IMPORTED=$([ -n "$R_URL" ] && echo YES || echo NO)"
  echo "CREDENTIAL_FILE_COUNT=$((GCOUNT + HCOUNT + ICOUNT + RCOUNT))"
  echo "RAW_LEGACY_FILES_IMPORTED=0"
  echo "LEGACY_HARDWARE_CONTROLLER_IMPORTED=NO"
  echo "LEGACY_PROFILE_MAP_IMPORTED=NO"
  echo "FOREIGN_PROJECT_IMPORTS=0"
  echo "MIGRATION_POLICY=EXPLICIT_KEY_ALLOWLIST_ONLY"
  echo "MIGRATED_AT=$(date +%s)"
} > "$TMP"
chmod 600 "$TMP"; mv -f "$TMP" "$MARK"
chmod -R go-rwx "$ROOT/recovery" "$ROOT/config" 2>/dev/null
