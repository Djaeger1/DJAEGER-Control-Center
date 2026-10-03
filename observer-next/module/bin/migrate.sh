#!/system/bin/sh
# DJAEGER AI clean credential migration.
# Only explicitly named DJAEGER AI credentials/identity fields are imported.
ROOT="$1"
LEGACY=${DJAEGER_LEGACY_ROOT:-/data/adb/djaeger_ai}
LEGACY_MODULE=${DJAEGER_LEGACY_MODULE_ROOT:-/data/adb/modules/djaeger_game_stabilizer}
MARK="$ROOT/recovery/migration.env"
CONFIG="$ROOT/config"
GEMINI="$CONFIG/gemini_vault.env"
HERMES="$CONFIG/hermes_cloud.env"
IDENTITY="$CONFIG/identity.env"
RAILWAY="$CONFIG/railway.env"

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

STATE=NO_LEGACY
TMP_KEYS="$ROOT/runtime/.migrate_gemini.$$"
TMP_SOURCES="$ROOT/runtime/.migration_sources.$$"
: > "$TMP_KEYS"
sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF' >> "$TMP_KEYS"

H_ACCESS="$(extract_exact HERMES_ACCESS_KEY "$HERMES")"
H_ENDPOINT="$(extract_exact HERMES_ENDPOINT "$HERMES")"
H_ID="$(extract_exact HERMES_CLOUD_ID "$HERMES")"
DEVICE_ID="$(extract_exact DEVICE_ID "$IDENTITY")"
R_TOKEN="$(extract_exact DJAEGER_ACCESS_TOKEN "$RAILWAY")"
G_MODEL="$(extract_exact GEMINI_MODEL "$CONFIG/gemini.env")"

STATE=NO_LEGACY
: > "$TMP_SOURCES"
for _root in "$LEGACY" "$LEGACY_MODULE"; do
  [ -d "$_root" ] || continue
  STATE=LEGACY_FOUND
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
if [ -n "$R_TOKEN" ]; then printf 'DJAEGER_ACCESS_TOKEN=%s\n' "$(safe_value "$R_TOKEN")" > "$RAILWAY.tmp.$$"; chmod 600 "$RAILWAY.tmp.$$"; mv -f "$RAILWAY.tmp.$$" "$RAILWAY"; fi

GCOUNT=$(sed -n 's/^KEY_[1-4]=//p' "$GEMINI" 2>/dev/null | awk 'NF{n++}END{print n+0}')
HCOUNT=0; [ -s "$HERMES" ] && HCOUNT=$(awk -F= 'NF>=2{n++}END{print n+0}' "$HERMES")
ICOUNT=0; [ -s "$IDENTITY" ] && ICOUNT=1
RCOUNT=0; [ -s "$RAILWAY" ] && RCOUNT=1
if [ "$GCOUNT" -gt 0 ] || [ "$HCOUNT" -gt 0 ] || [ "$ICOUNT" -gt 0 ] || [ "$RCOUNT" -gt 0 ]; then STATE=CLEAN_IMPORT_CREATED; else STATE=NO_CREDENTIALS_FOUND; fi

TMP="$MARK.tmp.$$"
{
  echo "MIGRATION_SCHEMA=4"
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_PATH=$LEGACY"
  echo "LEGACY_MODULE_PATH=$LEGACY_MODULE"
  echo "GEMINI_KEY_COUNT=$GCOUNT"
  echo "HERMES_FIELD_COUNT=$HCOUNT"
  echo "IDENTITY_IMPORTED=$([ "$ICOUNT" -gt 0 ] && echo YES || echo NO)"
  echo "RAILWAY_TOKEN_IMPORTED=$([ "$RCOUNT" -gt 0 ] && echo YES || echo NO)"
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
