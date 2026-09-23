#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
S="$M/bin/shadow.sh"
W="$R/runtime/contextual_shadow_v4_rangefix"
N="$W/shadow.new"
SN="$W/range.snip"
mkdir -p "$W" || exit 1

grep -Fq "CONTEXTUAL_SHADOW_V3_PARSEFIX" "$S" || {
  echo "CONTEXTUAL_SHADOW_V3_PARSEFIX=MISSING"
  exit 41
}

cat > "$SN" <<'EOF'
  # CONTEXTUAL_SHADOW_V4_RANGEFIX
  LMIN=$(kv LITTLE_MIN_KHZ "$POLICY"); LMAX=$(kv LITTLE_MAX_KHZ "$POLICY")
  BMIN=$(kv BIG_MIN_KHZ "$POLICY"); BMAX=$(kv BIG_MAX_KHZ "$POLICY")
  GMIN=$(kv GPU_MIN_HZ "$POLICY"); GMAX=$(kv GPU_MAX_HZ "$POLICY")
  case "$LMIN:$LMAX:$BMIN:$BMAX:$GMIN:$GMAX" in
    *[!0-9:]*|:*)
      publish REJECT invalid_candidate
      sleep 20
      continue
      ;;
  esac
EOF

if grep -Fq "CONTEXTUAL_SHADOW_V4_RANGEFIX" "$S"; then
  cp "$S" "$N" || exit 42
  echo "RANGE_FIX=ALREADY_PRESENT"
else
  COUNT=$(grep -c '^  # CONTEXTUAL_SHADOW_V2$' "$S" 2>/dev/null || true)
  echo "RANGE_INSERT_ANCHORS=$COUNT"
  [ "$COUNT" = 1 ] || exit 43

  awk -v SNIP="$SN" '
    BEGIN{done=0}
    {
      print
      if($0=="  # CONTEXTUAL_SHADOW_V2" && !done){
        while((getline x < SNIP)>0) print x
        close(SNIP)
        done=1
      }
    }
    END{if(done!=1) exit 44}
  ' "$S" > "$N" || exit 44
  echo "RANGE_FIX=INSERTED"
fi

if sh -n "$N"; then
  echo "SHADOW_CANDIDATE_SYNTAX=OK"
else
  echo "SHADOW_CANDIDATE_SYNTAX=FAIL"
  exit 51
fi

for MARK in   CONTEXTUAL_SHADOW_V2   CONTEXTUAL_SHADOW_V3_PARSEFIX   CONTEXTUAL_SHADOW_V4_RANGEFIX   PERSIST_REJECT_STRATEGY_MULTI   MULTIACTUATOR_PERSIST_NORMALIZE
do
  if grep -Fq "$MARK" "$N"; then
    echo "$MARK=OK"
  else
    echo "$MARK=MISSING"
    exit 52
  fi
done

TS=$(date +%s)
cp "$S" "$R/runtime/shadow.pre_contextual_v4_rangefix.$TS" || exit 61
cp "$N" "$S" || exit 62
chmod 755 "$S"

P=$(cat "$R/runtime/locks/shadow.lock/pid" 2>/dev/null)
case "$P" in
  ""|*[!0-9]*) ;;
  *)
    kill -TERM "$P" 2>/dev/null
    sleep 1
    kill -0 "$P" 2>/dev/null && kill -KILL "$P" 2>/dev/null
    ;;
esac
rm -rf "$R/runtime/locks/shadow.lock"
nohup sh "$S" "$R" "$M" >/dev/null 2>&1 &

echo "PATCH=CONTEXTUAL_SHADOW_V4_RANGEFIX_ACTIVE"
echo "SHADOW_SYNTAX=OK"
