#!/system/bin/sh

# Copy configuration/identity material into a private compatibility vault.
# The legacy state remains untouched. Runtime logs and old hardware controllers
# are deliberately excluded.

ROOT="$1"
LEGACY=${DJAEGER_LEGACY_ROOT:-/data/adb/djaeger_ai}
DEST="$ROOT/recovery/legacy"
MARK="$ROOT/recovery/migration.env"
FILES="$DEST/files"
DIRS="$DEST/dirs"

mkdir -p "$FILES" "$DIRS" "$ROOT/config"
chmod 700 "$ROOT/recovery" "$DEST" "$FILES" "$DIRS" "$ROOT/config" 2>/dev/null

STATE=NO_LEGACY
if [ -d "$LEGACY" ]; then
  STATE=LEGACY_FOUND

  # Known configuration trees are copied recursively because generic names
  # such as config.json or identity.env may not reveal their purpose.
  for d in config configs secret secrets identity cloud hermes gemini vault auth credentials; do
    [ -d "$LEGACY/$d" ] || continue
    mkdir -p "$DIRS/$d"
    cp -a "$LEGACY/$d/." "$DIRS/$d/" 2>/dev/null || true
  done

  # Also retain matching files from nested layouts while preserving paths.
  find "$LEGACY" -maxdepth 6 -type f 2>/dev/null | while IFS= read -r f; do
    rel=${f#"$LEGACY"/}
    name=${rel##*/}
    case "$name" in
      *[Kk][Ee][Yy]*|*[Tt][Oo][Kk][Ee][Nn]*|*[Ss][Ee][Cc][Rr][Ee][Tt]*|*[Hh][Ee][Rr][Mm][Ee][Ss]*|*[Gg][Ee][Mm][Ii][Nn][Ii]*|*[Cc][Ll][Oo][Uu][Dd]*|*[Ii][Dd][Ee][Nn][Tt][Ii][Tt][Yy]*|*device_id*|*client_id*|*.env|*.conf|*.json)
        out="$FILES/$rel"
        mkdir -p "${out%/*}"
        cp -p "$f" "$out" 2>/dev/null || true
      ;;
    esac
  done

  STATE=BACKUP_CREATED
fi

# HERMES Cloud credentials were historically also stored outside DJAEGER's
# state directory. Copy only the named credential file, never arbitrary files.
for f in \
  /data/user/0/com.termoneplus/app_HOME/hermes-cloud-deploy/hermes-cloud-djaeger/HERMES_CLOUD_CREDENTIALS.txt \
  /data/media/0/Download/HERMES_CLOUD_CREDENTIALS.txt \
  /sdcard/Download/HERMES_CLOUD_CREDENTIALS.txt; do
  [ -r "$f" ] || continue
  cp -p "$f" "$DEST/HERMES_CLOUD_CREDENTIALS.txt" 2>/dev/null || true
  STATE=BACKUP_CREATED
  break
done

COUNT=$(find "$DEST" -type f 2>/dev/null | wc -l | tr -d ' ')
case "$COUNT" in ''|*[!0-9]*) COUNT=0;; esac
PRESENT=NO; [ "$COUNT" -gt 0 ] 2>/dev/null && PRESENT=YES

TMP="$MARK.tmp.$$"
{
  echo "MIGRATION_SCHEMA=2"
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_PATH=$LEGACY"
  echo "LEGACY_CONFIG_PRESENT=$PRESENT"
  echo "CREDENTIAL_FILE_COUNT=$COUNT"
  echo "LEGACY_HARDWARE_CONTROLLER_IMPORTED=NO"
  echo "LEGACY_PROFILE_MAP_IMPORTED=NO"
  echo "MIGRATED_AT=$(date +%s)"
} > "$TMP"
chmod 600 "$TMP"
mv -f "$TMP" "$MARK"

chmod -R go-rwx "$ROOT/recovery" 2>/dev/null
