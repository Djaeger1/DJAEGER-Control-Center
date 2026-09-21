#!/system/bin/sh
# DJAEGER AI cleanroom credential migration.
# Imports only explicit DJAEGER AI credential/identity keys. It never copies
# legacy directories, controllers, profiles, runtime logs, or foreign-project files.

ROOT="$1"
LEGACY=${DJAEGER_LEGACY_ROOT:-/data/adb/djaeger_ai}
MARK="$ROOT/recovery/migration.env"
CONFIG="$ROOT/config"
GEMINI="$CONFIG/gemini_vault.env"
HERMES="$CONFIG/hermes_cloud.env"
IDENTITY="$CONFIG/identity.env"

mkdir -p "$ROOT/recovery" "$CONFIG"
chmod 700 "$ROOT/recovery" "$CONFIG" 2>/dev/null

forbidden_path(){
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | grep -Eq 'djaeger[-_ ]?work|hermes[-_ ]?work|/(work|studio|youtube|publisher|renderer)(/|[._-])'
}

safe_value(){
  printf '%s' "$1" | tr -d '\r\n' | cut -c1-1024
}

extract_exact(){
  _key="$1"; _file="$2"
  sed -n "s/^[[:space:]]*$_key[[:space:]]*=[[:space:]]*['\"]\{0,1\}\([^'\"[:space:]]\{1,1024\}\).*/\1/p" "$_file" 2>/dev/null | head -n1
}

STATE=NO_LEGACY
SCANNED=0
SKIPPED_FOREIGN=0
RAW_IMPORTED=0

TMP_KEYS="$ROOT/runtime/.migrate_gemini.$$"
mkdir -p "$ROOT/runtime"
: > "$TMP_KEYS"

# Preserve already-migrated cleanroom keys first.
sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF' >> "$TMP_KEYS"

H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$HERMES")"
H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$HERMES")"
H_ID="$(extract_exact HERMES_CLOUD_ID "$HERMES")"
DEVICE_ID="$(extract_exact DEVICE_ID "$IDENTITY")"
G_MODEL=""

if [ -d "$LEGACY" ]; then
  STATE=LEGACY_FOUND
  find "$LEGACY" -maxdepth 7 -type f 2>/dev/null | while IFS= read -r f; do
    forbidden_path "$f" && continue
    printf '%s\n' "$f"
  done > "$ROOT/runtime/.migration_sources.$$"

  while IFS= read -r f; do
    [ -r "$f" ] || continue
    SCANNED=$((SCANNED+1))

    # Gemini: only explicit Gemini key names. Generic API_KEY is intentionally rejected.
    for k in GEMINI_API_KEY KEY_1 KEY_2 KEY_3 KEY_4; do
      v="$(extract_exact "$k" "$f")"
      [ -n "$v" ] && printf '%s\n' "$(safe_value "$v")" >> "$TMP_KEYS"
    done
    [ -n "$G_MODEL" ] || G_MODEL="$(extract_exact GEMINI_MODEL "$f")"

    # HERMES: only explicit HERMES names from non-foreign paths.
    [ -n "$H_ACCESS" ] || H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$f")"
    [ -n "$H_ENDPOINT" ] || H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$f")"
    [ -n "$H_ID" ] || H_ID="$(extract_exact HERMES_CLOUD_ID "$f")"
    [ -n "$DEVICE_ID" ] || DEVICE_ID="$(extract_exact DEVICE_ID "$f")"
  done < "$ROOT/runtime/.migration_sources.$$"
  rm -f "$ROOT/runtime/.migration_sources.$$"
fi

# Historical HERMES Cloud export: exact filename only, explicit keys only.
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
if [ -s "$GEMINI.tmp.$$" ]; then
  chmod 600 "$GEMINI.tmp.$$"; mv -f "$GEMINI.tmp.$$" "$GEMINI"
else
  rm -f "$GEMINI.tmp.$$"
fi

if [ -n "$G_MODEL" ]; then
  printf 'GEMINI_MODEL=%s\n' "$(safe_value "$G_MODEL")" > "$CONFIG/gemini.env.tmp.$$"
  chmod 600 "$CONFIG/gemini.env.tmp.$$"; mv -f "$CONFIG/gemini.env.tmp.$$" "$CONFIG/gemini.env"
fi

{
  [ -n "$H_ACCESS" ] && printf 'HERMES_ACCESS_KEY=%s\n' "$(safe_value "$H_ACCESS")"
  [ -n "$H_ENDPOINT" ] && printf 'HERMES_ENDPOINT=%s\n' "$(safe_value "$H_ENDPOINT")"
  [ -n "$H_ID" ] && printf 'HERMES_CLOUD_ID=%s\n' "$(safe_value "$H_ID")"
} > "$HERMES.tmp.$$"
if [ -s "$HERMES.tmp.$$" ]; then chmod 600 "$HERMES.tmp.$$"; mv -f "$HERMES.tmp.$$" "$HERMES"; else rm -f "$HERMES.tmp.$$"; fi

if [ -n "$DEVICE_ID" ]; then
  printf 'DEVICE_ID=%s\n' "$(safe_value "$DEVICE_ID")" > "$IDENTITY.tmp.$$"
  chmod 600 "$IDENTITY.tmp.$$"; mv -f "$IDENTITY.tmp.$$" "$IDENTITY"
fi

GCOUNT=$(sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF{n++}END{print n+0}')
HCOUNT=0
[ -s "$HERMES" ] && HCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$HERMES")
ICOUNT=0
[ -s "$IDENTITY" ] && ICOUNT=1
[ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ] || STATE=NO_CREDENTIALS_FOUND
[ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ] || :
if [ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ]; then STATE=CLEAN_IMPORT_CREATED; fi

TMP="$MARK.tmp.$$"
{
  echo "MIGRATION_SCHEMA=3"
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_PATH=$LEGACY"
  echo "GEMINI_KEY_COUNT=$GCOUNT"
  echo "HERMES_FIELD_COUNT=$HCOUNT"
  echo "IDENTITY_IMPORTED=$([ "$ICOUNT" -gt 0 ] && echo YES || echo NO)"
  echo "CREDENTIAL_FILE_COUNT=$((GCOUNT + HCOUNT + ICOUNT))"
  echo "RAW_LEGACY_FILES_IMPORTED=0"
  echo "LEGACY_HARDWARE_CONTROLLER_IMPORTED=NO"
  echo "LEGACY_PROFILE_MAP_IMPORTED=NO"
  echo "FOREIGN_PROJECT_IMPORTS=0"
  echo "MIGRATION_POLICY=EXPLICIT_KEY_ALLOWLIST_ONLY"
  echo "MIGRATED_AT=$(date +%s)"
} > "$TMP"
chmod 600 "$TMP"
mv -f "$TMP" "$MARK"

chmod -R go-rwx "$ROOT/recovery" "$ROOT/config" 2>/dev/null
