#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
S="$M/bin/shadow.sh"
W="$R/runtime/contextual_shadow_v3_parsefix"
N="$W/shadow.new"
mkdir -p "$W" || exit 1

grep -Fq "CONTEXTUAL_SHADOW_V2" "$S" || {
  echo "CONTEXTUAL_SHADOW_V2=MISSING"
  exit 41
}

COUNT=$(grep -c '^    set -- $METRICS$' "$S" 2>/dev/null || true)
echo "PARSE_ANCHORS=$COUNT"
[ "$COUNT" = 1 ] || exit 42

awk '
  BEGIN{skip=0; done=0}
  {
    if(!skip && $0=="    set -- $METRICS"){
      print "    # CONTEXTUAL_SHADOW_V3_PARSEFIX"
      print "    METRICS_RAW=\"$METRICS\""
      print "    WINDOWS=$(printf \"%s\\n\" \"$METRICS\" | awk '\''{print $1}'\'')"
      print "    FPS_AVG=$(printf \"%s\\n\" \"$METRICS\" | awk '\''{print $2}'\'')"
      print "    JANK_AVG=$(printf \"%s\\n\" \"$METRICS\" | awk '\''{print $3}'\'')"
      print "    P95_AVG=$(printf \"%s\\n\" \"$METRICS\" | awk '\''{print $4}'\'')"
      print "    POWER_AVG=$(printf \"%s\\n\" \"$METRICS\" | awk '\''{print $5}'\'')"
      print "    POWER_N=$(printf \"%s\\n\" \"$METRICS\" | awk '\''{print $6}'\'')"
      print "    case \"$WINDOWS\" in \"\"|*[!0-9]*) WINDOWS=0;; esac"
      print "    case \"$POWER_N\" in \"\"|*[!0-9]*) POWER_N=0;; esac"
      skip=1
      done=1
      next
    }

    if(skip){
      if(index($0,"    if [ \"$WINDOWS\" -ge 60 ]")==1){
        skip=0
        print
      }
      next
    }

    print
  }
  END{
    if(skip || done!=1) exit 43
  }
' "$S" > "$N" || exit 43

if ! grep -Fq 'SHADOW_METRICS_RAW=' "$N"; then
  awk '
    {
      print
      if(index($0,"SHADOW_CONTEXT_HOURS=")>0 && !done){
        print "    echo \"SHADOW_METRICS_RAW=${METRICS_RAW:-NA}\""
        done=1
      }
    }
    END{if(!done) exit 44}
  ' "$N" > "$W/shadow.publish" || exit 44
  mv -f "$W/shadow.publish" "$N"
fi

if sh -n "$N"; then
  echo "SHADOW_CANDIDATE_SYNTAX=OK"
else
  echo "SHADOW_CANDIDATE_SYNTAX=FAIL"
  exit 51
fi

grep -Fq "CONTEXTUAL_SHADOW_V3_PARSEFIX" "$N" || exit 52
grep -Fq "PERSIST_REJECT_STRATEGY_MULTI" "$N" || exit 53
grep -Fq "MULTIACTUATOR_PERSIST_NORMALIZE" "$N" || exit 54

TS=$(date +%s)
cp "$S" "$R/runtime/shadow.pre_contextual_v3_parsefix.$TS" || exit 61
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

echo "PATCH=CONTEXTUAL_SHADOW_V3_PARSEFIX_ACTIVE"
echo "SHADOW_SYNTAX=OK"
