#!/system/bin/sh
ROOT="$1"
LEGACY=/data/adb/djaeger_ai
DEST="$ROOT/recovery/legacy"
MARK="$ROOT/recovery/migration.env"
ENGINE_ROOT="$ROOT/recovery/engine"
ENGINE_MOD="$ENGINE_ROOT/module"
ENGINE_MARK="$ENGINE_ROOT/engine.env"

mkdir -p "$DEST" "$ENGINE_MOD/system/bin" "$ENGINE_MOD/system/etc"
chmod 700 "$ROOT/recovery" "$DEST" "$ENGINE_ROOT" "$ENGINE_MOD" 2>/dev/null

if [ ! -f "$MARK" ]; then
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
fi

# Preserve only cognition helpers from the old module; never copy its controller,
# profile map, root executor or startup service.
SRC=""
for m in /data/adb/modules/djaeger_game_stabilizer /data/adb/modules/*; do
  [ -d "$m" ] || continue
  if [ -r "$m/system/bin/djaeger-hermes-local" ] || [ -r "$m/system/bin/djaeger-hermes-cloud" ]; then
    SRC="$m"
    break
  fi
done

if [ -n "$SRC" ]; then
  for f in "$SRC"/system/bin/djaeger-hermes-* "$SRC"/system/bin/djaeger-brain-status; do
    [ -f "$f" ] || continue
    cp -a "$f" "$ENGINE_MOD/system/bin/" 2>/dev/null
  done
  if [ -d "$SRC/system/etc/djaeger" ]; then
    rm -rf "$ENGINE_MOD/system/etc/djaeger" 2>/dev/null
    cp -a "$SRC/system/etc/djaeger" "$ENGINE_MOD/system/etc/" 2>/dev/null
  fi
  [ -r "$SRC/hardware_contract.conf" ] && cp -a "$SRC/hardware_contract.conf" "$ENGINE_MOD/" 2>/dev/null
  [ -r "$SRC/predictor.sh" ] && cp -a "$SRC/predictor.sh" "$ENGINE_MOD/predictor-legacy.sh" 2>/dev/null
fi

chmod -R go-rwx "$ROOT/recovery" 2>/dev/null
find "$ENGINE_MOD/system/bin" -type f -exec chmod 700 {} \; 2>/dev/null

HLOCAL=NO; HCLOUD=NO; GEMINI_LEGACY=NO
[ -r "$ENGINE_MOD/system/bin/djaeger-hermes-local" ] && HLOCAL=YES
[ -r "$ENGINE_MOD/system/bin/djaeger-hermes-cloud" ] && HCLOUD=YES
[ -r "$ENGINE_MOD/predictor-legacy.sh" ] && GEMINI_LEGACY=YES
T="$ENGINE_MARK.tmp.$$"
{
  echo "ENGINE_MIGRATION_STATE=$([ -n "$SRC" ] && echo RESTORED || echo SOURCE_NOT_FOUND)"
  echo "HERMES_LOCAL_HELPER=$HLOCAL"
  echo "HERMES_CLOUD_HELPER=$HCLOUD"
  echo "GEMINI_LEGACY_PREDICTOR=$GEMINI_LEGACY"
  echo "LEGACY_MODULE_SOURCE_PRESENT=$([ -n "$SRC" ] && echo YES || echo NO)"
  echo "UPDATED_AT=$(date +%s)"
} > "$T"
chmod 600 "$T"; mv -f "$T" "$ENGINE_MARK"
