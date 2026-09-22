#!/system/bin/sh
# DJAEGER AI Adaptive credential recovery.
# Restores only allowlisted DJAEGER AI credentials/configuration. Secret values
# are never copied to migration.env, logs, telemetry, or Control Center.

ROOT="$1"
LEGACY=${DJAEGER_LEGACY_ROOT:-/data/adb/djaeger_ai}
LEGACY_MODULE=${DJAEGER_LEGACY_MODULE_ROOT:-/data/adb/modules/djaeger_game_stabilizer}
CONFIG="$ROOT/config"
RUNTIME="$ROOT/runtime"
RECOVERY="$ROOT/recovery"
MARK="$RECOVERY/migration.env"

GEMINI="$CONFIG/gemini_vault.env"
GEMINI_SLOT="$CONFIG/gemini_slot"
GEMINI_COOLDOWN="$CONFIG/gemini_cooldown.env"
HERMES="$CONFIG/hermes_cloud.env"
IDENTITY="$CONFIG/identity.env"
RAILWAY="$CONFIG/railway.env"
NEURON="$CONFIG/hermes_neuron_legacy.env"

mkdir -p "$CONFIG" "$RUNTIME" "$RECOVERY"
chmod 700 "$CONFIG" "$RECOVERY" 2>/dev/null

extract_exact() {
  _key="$1"; _file="$2"
  [ -r "$_file" ] || return 0
  awk -v k="$_key" '
    index($0,k"=")==1 {
      v=substr($0,length(k)+2)
      gsub(/^[[:space:]]+|[[:space:]]+$/,"",v)
      if (substr(v,1,1)=="\047" && substr(v,length(v),1)=="\047") v=substr(v,2,length(v)-2)
      if (substr(v,1,1)=="\042" && substr(v,length(v),1)=="\042") v=substr(v,2,length(v)-2)
      print v
      exit
    }' "$_file" 2>/dev/null
}

safe_value() {
  printf '%s' "$1" | tr -d '\r\n' | cut -c1-1024
}

valid_key() {
  _v="$1"
  _n="$(printf '%s' "$_v" | wc -c | tr -d ' ')"
  case "$_n" in ''|*[!0-9]*) return 1;; esac
  [ "$_n" -ge 20 ] && [ "$_n" -le 256 ] || return 1
  printf '%s' "$_v" | grep -Eq '^[A-Za-z0-9._-]+$'
}

is_foreign_path() {
  _p="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  printf '%s' "$_p" | grep -Eq 'djaeger[-_ ]?work|hermes[-_ ]?work|/(youtube|renderer|studio|publisher)(/|[._-])'
}

append_key() {
  _v="$1"
  valid_key "$_v" && printf '%s\n' "$_v" >> "$TMP_KEYS"
}

num_value() {
  case "$1" in ''|*[!0-9]*) return 1;; *) printf '%s' "$1";; esac
}

TMP_KEYS="$RUNTIME/.migrate_keys.$$"
TMP_SOURCES="$RUNTIME/.migrate_sources.$$"
: > "$TMP_KEYS"
: > "$TMP_SOURCES"
chmod 600 "$TMP_KEYS" "$TMP_SOURCES" 2>/dev/null

LEGACY_PRESENT=NO
RAW_VAULT_FOUND=NO
COOLDOWN_FOUND=NO
HERMES_ALIAS_FOUND=NO
NEURON_PRESENT=NO

# Preserve already-restored values first.
sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | while IFS= read -r _k; do append_key "$_k"; done
H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$HERMES")"
H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$HERMES")"
H_ID="$(extract_exact HERMES_CLOUD_ID "$HERMES")"
DEVICE_ID="$(extract_exact DEVICE_ID "$IDENTITY")"
R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$RAILWAY")"
R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$RAILWAY")"
G_MODEL="$(extract_exact GEMINI_MODEL "$CONFIG/gemini.env")"
H_BASE=""
H_PATH=""

# Legacy Gemini format used by the old DJAEGER: one raw key per line.
if [ -r "$LEGACY/gemini_keys.vault" ]; then
  LEGACY_PRESENT=YES
  RAW_VAULT_FOUND=YES
  while IFS= read -r _k; do
    _k="$(printf '%s' "$_k" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    append_key "$_k"
  done < "$LEGACY/gemini_keys.vault"
fi

LEGACY_ACTIVE_KEY="$(extract_exact GEMINI_API_KEY "$LEGACY/gemini.conf")"
append_key "$LEGACY_ACTIVE_KEY"
[ -r "$LEGACY/gemini.conf" ] && LEGACY_PRESENT=YES

# Scan only DJAEGER roots and only import allowlisted key names.
for _root in "$LEGACY" "$LEGACY_MODULE"; do
  [ -d "$_root" ] || continue
  LEGACY_PRESENT=YES
  find "$_root" -maxdepth 7 -type f -size -256k 2>/dev/null | while IFS= read -r _f; do
    is_foreign_path "$_f" && continue
    printf '%s\n' "$_f"
  done >> "$TMP_SOURCES"
done

# RUNTIMEFIX1: old DJAEGER recovery flows also left credential/config backups
# in Termux and Download. Scan only known credential filenames.
for _root in /data/user/0/com.termoneplus/app_HOME /data/media/0/Download /sdcard/Download; do
  [ -d "$_root" ] || continue
  find "$_root" -maxdepth 8 -type f -size -256k \( \
    -name 'gemini_keys.vault*' -o -name 'gemini.conf*' -o -name 'gemini_key_cooldowns*' -o \
    -name 'hermes_cloud.conf*' -o -name 'HERMES_CLOUD_CREDENTIALS.txt*' -o -name 'neuron_budget.env*' \
  \) 2>/dev/null | while IFS= read -r _f; do
    is_foreign_path "$_f" && continue
    printf '%s\n' "$_f"
  done >> "$TMP_SOURCES"
done
awk 'NF&&!seen[$0]++' "$TMP_SOURCES" > "$TMP_SOURCES.uniq" 2>/dev/null || :
mv -f "$TMP_SOURCES.uniq" "$TMP_SOURCES" 2>/dev/null || true

while IFS= read -r _f; do
  [ -r "$_f" ] || continue
  case "$(basename "$_f")" in
    gemini_keys.vault*)
      RAW_VAULT_FOUND=YES
      while IFS= read -r _raw_key; do
        _raw_key="$(printf '%s' "$_raw_key" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        append_key "$_raw_key"
      done < "$_f"
      ;;
  esac
  for _name in GEMINI_API_KEY KEY_1 KEY_2 KEY_3 KEY_4; do
    append_key "$(extract_exact "$_name" "$_f")"
  done

  [ -n "$G_MODEL" ] || G_MODEL="$(extract_exact GEMINI_MODEL "$_f")"
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$_f")"
  if [ -z "$H_ACCESS" ]; then
    H_ACCESS="$(extract_exact HERMES_SHARED_TOKEN "$_f")"
    [ -n "$H_ACCESS" ] && HERMES_ALIAS_FOUND=YES
  fi
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$_f")"
  [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$_f")"
  [ -n "$R_TOKEN" ] || R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$_f")"
  [ -n "$R_URL" ] || R_URL="$(extract_exact DJAEGER_RAILWAY_URL "$_f")"

  _hep="$(extract_exact HERMES_ENDPOINT "$_f")"
  case "$_hep" in
    https://*) [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$_hep" ;;
    /*) [ -n "$H_PATH" ] || H_PATH="$_hep" ;;
  esac
  _base="$(extract_exact ENDPOINT "$_f")"
  case "$_base" in https://*) [ -n "$H_BASE" ] || H_BASE="$_base";; esac
done < "$TMP_SOURCES"
rm -f "$TMP_SOURCES"

# Explicit Hermes backup locations that existed in the earlier deployment flow.
for _f in   "$LEGACY/hermes_cloud.conf"   "$LEGACY/HERMES_CLOUD_CREDENTIALS.txt"   /data/user/0/com.termoneplus/app_HOME/hermes-cloud-deploy/hermes-cloud-djaeger/HERMES_CLOUD_CREDENTIALS.txt   /data/media/0/Download/HERMES_CLOUD_CREDENTIALS.txt   /sdcard/Download/HERMES_CLOUD_CREDENTIALS.txt
do
  [ -r "$_f" ] || continue
  LEGACY_PRESENT=YES
  [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$_f")"
  if [ -z "$H_ACCESS" ]; then
    H_ACCESS="$(extract_exact HERMES_SHARED_TOKEN "$_f")"
    [ -n "$H_ACCESS" ] && HERMES_ALIAS_FOUND=YES
  fi
  [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$_f")"
  [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$_f")"
  _hep="$(extract_exact HERMES_ENDPOINT "$_f")"
  case "$_hep" in
    https://*) [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$_hep" ;;
    /*) [ -n "$H_PATH" ] || H_PATH="$_hep" ;;
  esac
  _base="$(extract_exact ENDPOINT "$_f")"
  case "$_base" in https://*) [ -n "$H_BASE" ] || H_BASE="$_base";; esac
done

# Legacy Hermes could store a base ENDPOINT plus a relative HERMES_ENDPOINT.
case "$H_ENDPOINT" in
  https://*) : ;;
  *)
    case "$H_BASE" in
      https://*)
        H_BASE="$(printf '%s' "$H_BASE" | sed 's:/*$::')"
        case "$H_PATH" in
          /*) H_ENDPOINT="$H_BASE$H_PATH" ;;
          *) H_ENDPOINT="$H_BASE" ;;
        esac
      ;;
    esac
  ;;
esac

# Deduplicate and keep exactly four Gemini keys.
awk 'NF && !seen[$0]++ {n++; if(n<=4) print "KEY_" n "=" $0}' "$TMP_KEYS" > "$GEMINI.tmp.$$"
rm -f "$TMP_KEYS"
if [ -s "$GEMINI.tmp.$$" ]; then
  chmod 600 "$GEMINI.tmp.$$"
  mv -f "$GEMINI.tmp.$$" "$GEMINI"
else
  rm -f "$GEMINI.tmp.$$"
fi

# Preserve/restore selected slot by matching the legacy active key.
if [ -n "$LEGACY_ACTIVE_KEY" ] && [ -r "$GEMINI" ]; then
  _slot="$(awk -F= -v k="$LEGACY_ACTIVE_KEY" '$2==k{sub(/^KEY_/,"",$1);print $1;exit}' "$GEMINI" 2>/dev/null)"
  case "$_slot" in
    1|2|3|4) printf '%s\n' "$_slot" > "$GEMINI_SLOT"; chmod 600 "$GEMINI_SLOT" ;;
  esac
fi
GCOUNT="$(sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF{n++}END{print n+0}')"
case "$GCOUNT" in ''|*[!0-9]*) GCOUNT=0;; esac
_slot="$(cat "$GEMINI_SLOT" 2>/dev/null)"
case "$_slot" in 1|2|3|4) [ "$_slot" -le "$GCOUNT" ] 2>/dev/null || printf '1\n' > "$GEMINI_SLOT";; *) [ "$GCOUNT" -gt 0 ] 2>/dev/null && printf '1\n' > "$GEMINI_SLOT";; esac
[ -e "$GEMINI_SLOT" ] && chmod 600 "$GEMINI_SLOT"

# Legacy cooldown ledger is slot|until|reason.
COOLDOWN_SRC="$LEGACY/gemini_key_cooldowns"
[ -r "$COOLDOWN_SRC" ] || COOLDOWN_SRC="$(find "$LEGACY" /data/user/0/com.termoneplus/app_HOME /data/media/0/Download /sdcard/Download -maxdepth 8 -type f -name 'gemini_key_cooldowns*' 2>/dev/null | head -n1)"
if [ -r "$COOLDOWN_SRC" ]; then
  COOLDOWN_FOUND=YES
  grep -E '^KEY_[1-4]_UNTIL=[0-9]+$' "$GEMINI_COOLDOWN" 2>/dev/null > "$GEMINI_COOLDOWN.tmp.$$" || :
  while IFS='|' read -r _slot _until _reason; do
    case "$_slot" in 1|2|3|4) :;; *) continue;; esac
    case "$_until" in ''|*[!0-9]*) continue;; esac
    grep -v "^KEY_${_slot}_UNTIL=" "$GEMINI_COOLDOWN.tmp.$$" > "$GEMINI_COOLDOWN.tmp2.$$" 2>/dev/null || :
    mv -f "$GEMINI_COOLDOWN.tmp2.$$" "$GEMINI_COOLDOWN.tmp.$$"
    printf 'KEY_%s_UNTIL=%s\n' "$_slot" "$_until" >> "$GEMINI_COOLDOWN.tmp.$$"
  done < "$COOLDOWN_SRC"
  if [ -s "$GEMINI_COOLDOWN.tmp.$$" ]; then
    chmod 600 "$GEMINI_COOLDOWN.tmp.$$"
    mv -f "$GEMINI_COOLDOWN.tmp.$$" "$GEMINI_COOLDOWN"
  else
    rm -f "$GEMINI_COOLDOWN.tmp.$$"
  fi
fi
unset LEGACY_ACTIVE_KEY

if [ -n "$G_MODEL" ]; then
  printf 'GEMINI_MODEL=%s\n' "$(safe_value "$G_MODEL")" > "$CONFIG/gemini.env.tmp.$$"
  chmod 600 "$CONFIG/gemini.env.tmp.$$"
  mv -f "$CONFIG/gemini.env.tmp.$$" "$CONFIG/gemini.env"
fi

{
  [ -n "$H_ACCESS" ] && printf 'HERMES_ACCESS_KEY=%s\n' "$(safe_value "$H_ACCESS")"
  [ -n "$H_ENDPOINT" ] && printf 'HERMES_ENDPOINT=%s\n' "$(safe_value "$H_ENDPOINT")"
  [ -n "$H_ID" ] && printf 'HERMES_CLOUD_ID=%s\n' "$(safe_value "$H_ID")"
} > "$HERMES.tmp.$$"
if [ -s "$HERMES.tmp.$$" ]; then
  chmod 600 "$HERMES.tmp.$$"
  mv -f "$HERMES.tmp.$$" "$HERMES"
else
  rm -f "$HERMES.tmp.$$"
fi

if [ -n "$DEVICE_ID" ]; then
  printf 'DEVICE_ID=%s\n' "$(safe_value "$DEVICE_ID")" > "$IDENTITY.tmp.$$"
  chmod 600 "$IDENTITY.tmp.$$"
  mv -f "$IDENTITY.tmp.$$" "$IDENTITY"
fi

if [ -n "$R_TOKEN" ] || [ -n "$R_URL" ]; then
  {
    [ -n "$R_TOKEN" ] && printf 'DJAEGER_ACCESS_TOKEN=%s\n' "$(safe_value "$R_TOKEN")"
    [ -n "$R_URL" ] && printf 'DJAEGER_RAILWAY_URL=%s\n' "$(safe_value "$R_URL")"
  } > "$RAILWAY.tmp.$$"
  chmod 600 "$RAILWAY.tmp.$$"
  mv -f "$RAILWAY.tmp.$$" "$RAILWAY"
fi

# Import old device-side Neuron estimate without pretending it is provider truth.
NEURON_SRC="$LEGACY/hermes/neuron_budget.env"
[ -r "$NEURON_SRC" ] || NEURON_SRC="$(find "$LEGACY" /data/user/0/com.termoneplus/app_HOME /data/media/0/Download /sdcard/Download -maxdepth 8 -type f -name 'neuron_budget.env*' 2>/dev/null | head -n1)"
if [ -r "$NEURON_SRC" ]; then
  N_USED="$(extract_exact USED_EST "$NEURON_SRC")"
  N_LIMIT="$(extract_exact LIMIT "$NEURON_SRC")"
  N_DAY="$(extract_exact EPOCH_DAY "$NEURON_SRC")"
  N_FAST="$(extract_exact FAST_CALLS "$NEURON_SRC")"
  N_SMART="$(extract_exact SMART_CALLS "$NEURON_SRC")"
  N_DEEP="$(extract_exact DEEP_CALLS "$NEURON_SRC")"
  if num_value "$N_USED" >/dev/null && num_value "$N_LIMIT" >/dev/null; then
    {
      echo "SOURCE=LEGACY_LOCAL_ACCOUNTING"
      echo "ESTIMATED=YES"
      echo "USED_EST=$N_USED"
      echo "LIMIT=$N_LIMIT"
      num_value "$N_DAY" >/dev/null && echo "EPOCH_DAY=$N_DAY"
      num_value "$N_FAST" >/dev/null && echo "FAST_CALLS=$N_FAST"
      num_value "$N_SMART" >/dev/null && echo "SMART_CALLS=$N_SMART"
      num_value "$N_DEEP" >/dev/null && echo "DEEP_CALLS=$N_DEEP"
      echo "IMPORTED_AT=$(date +%s)"
    } > "$NEURON.tmp.$$"
    chmod 600 "$NEURON.tmp.$$"
    mv -f "$NEURON.tmp.$$" "$NEURON"
    NEURON_PRESENT=YES
  fi
fi

HCOUNT=0
[ -s "$HERMES" ] && HCOUNT="$(awk -F= 'NF>=2{n++}END{print n+0}' "$HERMES")"
case "$HCOUNT" in ''|*[!0-9]*) HCOUNT=0;; esac
ICOUNT=0; [ -s "$IDENTITY" ] && ICOUNT=1
RCOUNT=0; [ -s "$RAILWAY" ] && RCOUNT="$(awk -F= 'NF>=2{n++}END{print n+0}' "$RAILWAY")"
case "$RCOUNT" in ''|*[!0-9]*) RCOUNT=0;; esac

H_ACCESS_PRESENT=NO; [ -n "$H_ACCESS" ] && H_ACCESS_PRESENT=YES
H_ENDPOINT_PRESENT=NO; [ -n "$H_ENDPOINT" ] && H_ENDPOINT_PRESENT=YES
H_ID_PRESENT=NO; [ -n "$H_ID" ] && H_ID_PRESENT=YES

STATE=NO_CREDENTIALS_FOUND
if [ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ] || [ "$RCOUNT" -gt 0 ]; then STATE=PARTIAL_RECOVERY; fi
if [ "$GCOUNT" -eq 4 ] && [ "$H_ACCESS_PRESENT" = YES ] && [ "$H_ENDPOINT_PRESENT" = YES ]; then STATE=RECOVERED; fi

{
  echo "MIGRATION_SCHEMA=9"
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_CONFIG_PRESENT=$LEGACY_PRESENT"
  echo "RAW_GEMINI_VAULT_FOUND=$RAW_VAULT_FOUND"
  echo "GEMINI_COOLDOWN_FOUND=$COOLDOWN_FOUND"
  echo "GEMINI_KEY_COUNT=$GCOUNT"
  echo "HERMES_ALIAS_FOUND=$HERMES_ALIAS_FOUND"
  echo "HERMES_FIELD_COUNT=$HCOUNT"
  echo "HERMES_ACCESS_KEY_PRESENT=$H_ACCESS_PRESENT"
  echo "HERMES_ENDPOINT_PRESENT=$H_ENDPOINT_PRESENT"
  echo "HERMES_CLOUD_ID_PRESENT=$H_ID_PRESENT"
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
  echo "CREDENTIAL_SCAN_SCOPE=LEGACY_BACKUPS_TERMUX_DOWNLOAD"
  echo "SECRET_VALUES=HIDDEN"
  echo "MIGRATED_AT=$(date +%s)"
} > "$MARK.tmp.$$"
chmod 600 "$MARK.tmp.$$"
mv -f "$MARK.tmp.$$" "$MARK"
chmod -R go-rwx "$CONFIG" "$RECOVERY" 2>/dev/null

unset H_ACCESS R_TOKEN
exit 0
