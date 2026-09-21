#!/system/bin/sh
ROOT="$1"
LEGACY=/data/adb/djaeger_ai
DEST="$ROOT/recovery/legacy"
MARK="$ROOT/recovery/migration.env"

mkdir -p "$DEST"
chmod 700 "$DEST" 2>/dev/null
[ -f "$MARK" ] && exit 0

STATE=NO_LEGACY
if [ -d "$LEGACY" ]; then
  STATE=LEGACY_FOUND
  for d in config configs secret secrets identity cloud hermes gemini vault auth credentials; do
    [ -e "$LEGACY/$d" ] && cp -a "$LEGACY/$d" "$DEST/" 2>/dev/null
  done

  find "$LEGACY" -maxdepth 1 -type f 2>/dev/null | while read -r f; do
    n=$(basename "$f")
    case "$n" in
      *[Kk][Ee][Yy]*|*[Tt][Oo][Kk][Ee][Nn]*|*[Ss][Ee][Cc][Rr][Ee][Tt]*|*[Hh][Ee][Rr][Mm][Ee][Ss]*|*[Gg][Ee][Mm][Ii][Nn][Ii]*|*[Cc][Ll][Oo][Uu][Dd]*|*identity*|*device_id*|*.env)
        cp -a "$f" "$DEST/$n" 2>/dev/null ;;
    esac
  done
  STATE=BACKUP_CREATED
fi

chmod -R go-rwx "$ROOT/recovery" 2>/dev/null
PRESENT=NO
find "$DEST" -type f 2>/dev/null | head -n1 | grep -q . && PRESENT=YES
TMP="$MARK.tmp.$$"
{
  echo "MIGRATION_STATE=$STATE"
  echo "LEGACY_PATH=$LEGACY"
  echo "LEGACY_CONFIG_PRESENT=$PRESENT"
  echo "MIGRATED_AT=$(date +%s)"
} > "$TMP"
chmod 600 "$TMP"
mv -f "$TMP" "$MARK"
