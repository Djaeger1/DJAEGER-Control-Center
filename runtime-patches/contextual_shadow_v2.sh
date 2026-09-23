#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
S="$M/bin/shadow.sh"
W="$R/runtime/contextual_shadow_v2"
N="$W/shadow.new"
SNIP="$W/contextual.snip"
mkdir -p "$W" || exit 1

cat > "$SNIP" <<'EOF'
  # CONTEXTUAL_SHADOW_V2
  # Context hierarchy: freshest sufficiently-populated matching stock cohort.
  # Candidate range + CPU load +/-20% + skin +/-3C.
  CUR_CPU=$(kv CPU_AVG_KHZ "$SNAP")
  CUR_SKIN=$(kv SKIN_TEMP_C "$SNAP")
  case "$CUR_CPU" in ''|NA|*[!0-9.]*) CUR_CPU=0;; esac
  case "$CUR_SKIN" in ''|NA|*[!0-9.]*) CUR_SKIN=0;; esac

  CONTEXT_TIER=NONE
  CONTEXT_HOURS=0
  WINDOWS=0
  FPS_AVG=0
  JANK_AVG=0
  P95_AVG=0
  POWER_AVG=0
  POWER_N=0

  for CONTEXT_HOURS in 1 6 24; do
    CUTOFF=$((NOW-CONTEXT_HOURS*3600))
    METRICS=$(awk -F, -v p="$PKG" -v cutoff="$CUTOFF" \
      -v ca="$CUR_CPU" -v cs="$CUR_SKIN" \
      -v l0="$LMIN" -v l1="$LMAX" \
      -v b0="$BMIN" -v b1="$BMAX" \
      -v g0="$GMIN" -v g1="$GMAX" '
      NR>1 && $1+0>=cutoff && $3==p && $23=="STOCK_BASELINE" &&
      $20+0>=20 && $21~/^[0-9]+$/ && !seen[$21]++ &&
      $7+0>=l0 && $7+0<=l1 &&
      $8+0>=b0 && $8+0<=b1 &&
      $9+0>=g0 && $9+0<=g1 {
        cpuok=1
        if(ca>0 && $4+0>0) cpuok=($4>=ca*0.80 && $4<=ca*1.20)
        skinok=1
        if(cs>0 && $10+0>0) skinok=($10>=cs-3 && $10<=cs+3)
        if(cpuok && skinok){
          n++
          if($16~/^[0-9]+([.][0-9]+)?$/){fps+=$16; nf++}
          if($17~/^[0-9]+([.][0-9]+)?$/){jank+=$17; nj++}
          if($18~/^[0-9]+([.][0-9]+)?$/){p95+=$18; np++}
          if($14~/^[0-9]+([.][0-9]+)?$/ && $14+0>0){pn++; power+=$14}
        }
      }
      END{
        printf "%d ",n+0
        if(nf>0) printf "%.3f ",fps/nf; else printf "0 "
        if(nj>0) printf "%.3f ",jank/nj; else printf "0 "
        if(np>0) printf "%.3f ",p95/np; else printf "0 "
        if(pn>0) printf "%.3f %d",power/pn,pn; else printf "0 0"
      }' "$HISTORY" 2>/dev/null)

    set -- $METRICS
    WINDOWS=${1:-0}
    FPS_AVG=${2:-0}
    JANK_AVG=${3:-0}
    P95_AVG=${4:-0}
    POWER_AVG=${5:-0}
    POWER_N=${6:-0}

    if [ "$WINDOWS" -ge 60 ] 2>/dev/null && [ "$POWER_N" -ge 20 ] 2>/dev/null; then
      CONTEXT_TIER="CTX${CONTEXT_HOURS}H"
      break
    fi
  done

  if [ "$CONTEXT_TIER" = NONE ]; then
    publish WAITING insufficient_contextual_evidence
    sleep 20
    continue
  fi

EOF

START_COUNT=$(grep -c '^  CUTOFF=$((NOW-86400))$' "$S" 2>/dev/null || true)
END_COUNT=$(grep -c '^  INTENT=$(kv INTENT "$POLICY");' "$S" 2>/dev/null || true)

echo "CONTEXT_START_MARKERS=$START_COUNT"
echo "CONTEXT_END_MARKERS=$END_COUNT"

[ "$START_COUNT" = 1 ] || exit 41
[ "$END_COUNT" = 1 ] || exit 42

awk -v SNIP="$SNIP" '
  BEGIN{skip=0; inserted=0; starts=0; ends=0}
  {
    if(!skip && index($0,"  CUTOFF=$((NOW-86400))")==1){
      starts++
      skip=1
      while((getline x < SNIP)>0) print x
      close(SNIP)
      inserted=1
      next
    }

    if(skip && index($0,"  INTENT=$(kv INTENT ")==1){
      ends++
      skip=0
      print
      next
    }

    if(skip) next
    print
  }
  END{
    if(skip || !inserted || starts!=1 || ends!=1) exit 43
  }
' "$S" > "$N" || exit 43

if ! grep -Fq 'SHADOW_CONTEXT_TIER=' "$N"; then
  awk '
    {
      print
      if(index($0,"SHADOW_POWER_WINDOWS=")>0 && !done){
        print "    echo \"SHADOW_CONTEXT_TIER=${CONTEXT_TIER:-NONE}\""
        print "    echo \"SHADOW_CONTEXT_HOURS=${CONTEXT_HOURS:-0}\""
        done=1
      }
    }
    END{if(!done) exit 44}
  ' "$N" > "$W/shadow.publish" || exit 44
  mv -f "$W/shadow.publish" "$N"
fi

sh -n "$N" || exit 51
grep -Fq "CONTEXTUAL_SHADOW_V2" "$N" || exit 52
grep -Fq 'SHADOW_CONTEXT_TIER=' "$N" || exit 53
grep -Fq "PERSIST_REJECT_STRATEGY_MULTI" "$N" || exit 54
grep -Fq "MULTIACTUATOR_PERSIST_NORMALIZE" "$N" || exit 55

TS=$(date +%s)
cp "$S" "$R/runtime/shadow.pre_contextual_v2.$TS" || exit 61
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

echo "PATCH=CONTEXTUAL_SHADOW_V2_ACTIVE"
echo "SHADOW_SYNTAX=OK"
