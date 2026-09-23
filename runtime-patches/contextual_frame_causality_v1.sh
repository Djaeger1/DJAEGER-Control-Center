#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
S="$M/bin/shadow.sh"
W="$R/runtime/contextual_frame_causality_v1"
HN="$W/hermes.new"
SN="$W/shadow.new"
HELP="$W/helpers.snip"
BARRIER="$W/barrier.snip"
mkdir -p "$W" || exit 1

cat > "$HELP" <<'EOF'
# CONTEXTUAL_HEALTHY_FRAME_OVERRIDE_V1
contextual_healthy_ref(){
  _hf="$ROOT/history/telemetry.csv"
  [ -r "$_hf" ] || return 1
  _hp=$(kv ACTIVE_PACKAGE "$SNAP")
  _hc=$(num "$(kv CPU_AVG_KHZ "$SNAP")")
  _hs=$(num "$(kv SKIN_TEMP_C "$SNAP")")
  _hn=$(date +%s)
  _hcut=$((_hn-3600))

  _hr=$(awk -F, -v p="$_hp" -v cutoff="$_hcut" -v ca="$_hc" -v cs="$_hs" '
    NR>1 && $1+0>=cutoff && $3==p && $23=="STOCK_BASELINE" &&
    $20+0>=20 && $21~/^[0-9]+$/ && !seen[$21]++ {
      cpuok=1
      if(ca>0 && $4+0>0) cpuok=($4>=ca*0.80 && $4<=ca*1.20)
      skinok=1
      if(cs>0 && $10+0>0) skinok=($10>=cs-3 && $10<=cs+3)
      if(cpuok && skinok && $18+0<=20 && $16+0>=54 && $17+0<=5){
        n++; f+=$16; j+=$17; q+=$18; z+=$19
      }
    }
    END{
      if(n>0) printf "%d %.3f %.3f %.3f %.3f",n,f/n,j/n,q/n,z/n
      else printf "0 0 0 0 0"
    }
  ' "$_hf" 2>/dev/null)

  HR_N=$(printf "%s\n" "$_hr" | awk '{print $1}')
  HR_FPS=$(printf "%s\n" "$_hr" | awk '{print $2}')
  HR_JANK=$(printf "%s\n" "$_hr" | awk '{print $3}')
  HR_P95=$(printf "%s\n" "$_hr" | awk '{print $4}')
  HR_P99=$(printf "%s\n" "$_hr" | awk '{print $5}')
  case "$HR_N" in ''|*[!0-9]*) HR_N=0;; esac
  [ "$HR_N" -ge 60 ]
}

frame_degraded(){
  _fps=$(num "$(kv FPS_EST "$SNAP")")
  _jank=$(num "$(kv JANK_PCT "$SNAP")")
  _p95=$(num "$(kv P95_MS "$SNAP")")

  if contextual_healthy_ref; then
    _bfps="$HR_FPS"; _bjank="$HR_JANK"; _bp95="$HR_P95"
  else
    _bfps=$(num "$(kv FPS_P50 "$LEARN")")
    _bjank=$(num "$(kv JANK_P95 "$LEARN")")
    _bp95=$(num "$(kv FRAME_P95_P95_MS "$LEARN")")
  fi

  awk -v f="$_fps" -v j="$_jank" -v p="$_p95" \
      -v bf="$_bfps" -v bj="$_bjank" -v bp="$_bp95" 'BEGIN{
    if(bf<=0 || bp<=0) exit 1
    bad=(f>0 && f<bf*0.98) || (p>0 && p>bp*1.08)
    if(j>=0 && bj>=0 && j>bj*1.20+1) bad=1
    exit bad?0:1
  }'
}

frame_critical(){
  _fps=$(num "$(kv FPS_EST "$SNAP")")
  _j=$(num "$(kv JANK_PCT "$SNAP")")
  _p95=$(num "$(kv P95_MS "$SNAP")")
  _p99=$(num "$(kv P99_MS "$SNAP")")

  if contextual_healthy_ref; then
    _bfps="$HR_FPS"; _bj="$HR_JANK"; _bp95="$HR_P95"; _bp99="$HR_P99"
  else
    _bfps=$(num "$(kv FPS_P50 "$LEARN")")
    _bj=$(num "$(kv JANK_P95 "$LEARN")")
    _bp95=$(num "$(kv FRAME_P95_P95_MS "$LEARN")")
    _bp99=$(num "$(kv FRAME_P99_P95_MS "$LEARN")")
  fi

  awk -v f="$_fps" -v bf="$_bfps" -v j="$_j" -v bj="$_bj" \
      -v p="$_p95" -v bp="$_bp95" -v q="$_p99" -v bq="$_bp99" 'BEGIN{
    bad=(bf>0&&f>0&&f<bf*0.80)||(bp>0&&p>bp*1.25)||(bq>0&&q>bq*1.25)
    if(bj>=0&&j>bj*1.50+2) bad=1
    exit bad?0:1
  }'
}

frame_recovery_boost_supported(){
  _cf="$ROOT/history/telemetry.csv"
  [ -r "$_cf" ] || return 0
  _cp=$(kv ACTIVE_PACKAGE "$SNAP")
  _cc=$(num "$(kv CPU_AVG_KHZ "$SNAP")")
  _cs=$(num "$(kv SKIN_TEMP_C "$SNAP")")
  _cn=$(date +%s)
  _ccut=$((_cn-3600))

  _cr=$(awk -F, -v p="$_cp" -v cutoff="$_ccut" -v ca="$_cc" -v cs="$_cs" '
    NR>1 && $1+0>=cutoff && $3==p && $23=="STOCK_BASELINE" &&
    $20+0>=20 && $21~/^[0-9]+$/ && !seen[$21]++ {
      cpuok=1
      if(ca>0 && $4+0>0) cpuok=($4>=ca*0.80 && $4<=ca*1.20)
      skinok=1
      if(cs>0 && $10+0>0) skinok=($10>=cs-3 && $10<=cs+3)
      if(!(cpuok && skinok)) next

      if($18+0<=20 && $16+0>=54 && $17+0<=5){
        sn++; sl+=$7; sb+=$8; sg+=$9; sw+=$14
      }
      if($18+0>=25 || $16+0<50 || $17+0>15){
        bn++; bl+=$7; bb+=$8; bg+=$9; bw+=$14
      }
    }
    END{
      if(sn>0 && bn>0)
        printf "%d %d %.0f %.0f %.0f %.1f %.0f %.0f %.0f %.1f",
          sn,bn,sl/sn,sb/sn,sg/sn,sw/sn,bl/bn,bb/bn,bg/bn,bw/bn
      else
        printf "%d %d 0 0 0 0 0 0 0 0",sn+0,bn+0
    }
  ' "$_cf" 2>/dev/null)

  CR_SN=$(printf "%s\n" "$_cr" | awk '{print $1}')
  CR_BN=$(printf "%s\n" "$_cr" | awk '{print $2}')
  CR_SL=$(printf "%s\n" "$_cr" | awk '{print $3}')
  CR_SB=$(printf "%s\n" "$_cr" | awk '{print $4}')
  CR_SG=$(printf "%s\n" "$_cr" | awk '{print $5}')
  CR_SW=$(printf "%s\n" "$_cr" | awk '{print $6}')
  CR_BL=$(printf "%s\n" "$_cr" | awk '{print $7}')
  CR_BB=$(printf "%s\n" "$_cr" | awk '{print $8}')
  CR_BG=$(printf "%s\n" "$_cr" | awk '{print $9}')
  CR_BW=$(printf "%s\n" "$_cr" | awk '{print $10}')

  case "$CR_SN:$CR_BN" in *[!0-9:]*) return 0;; esac
  [ "$CR_SN" -ge 60 ] && [ "$CR_BN" -ge 60 ] || return 0

  # If bad-frame windows already run at >=95% of smooth clocks and power,
  # there is no empirical evidence that a clock boost is the missing resource.
  if awk -v sl="$CR_SL" -v sb="$CR_SB" -v sg="$CR_SG" -v sw="$CR_SW" \
         -v bl="$CR_BL" -v bb="$CR_BB" -v bg="$CR_BG" -v bw="$CR_BW" 'BEGIN{
      unsupported=(sl>0&&sb>0&&sg>0&&sw>0 &&
                   bl>=sl*0.95 && bb>=sb*0.95 && bg>=sg*0.95 && bw>=sw*0.95)
      exit unsupported?0:1
    }'; then
    return 1
  fi
  return 0
}

EOF

cat > "$BARRIER" <<'EOF'
  # FRAME_RECOVERY_CAUSAL_OBSERVE_BARRIER
  if [ "$HDETAIL" = local_frame_recovery_boost_not_supported_by_history ]; then
    rm -f "$HPLAN" "$LOCAL_OUT"
    HLOCAL_STATE=TAKEOVER_OBSERVE
    HACTIVE_SOURCE=HERMES_LOCAL
    HCLOUD_STATE=REACHABLE_IDLE
    HCLOUD_USED=NO
    write_state HERMES_TAKEOVER
    sleep 15
    continue
  fi

EOF

# Insert contextual override immediately before local_synthesize_takeover.
if grep -Fq "CONTEXTUAL_HEALTHY_FRAME_OVERRIDE_V1" "$H"; then
  cp "$H" "$HN" || exit 41
  echo "FRAME_OVERRIDE=ALREADY_PRESENT"
else
  C=$(grep -c '^local_synthesize_takeover(){$' "$H" 2>/dev/null || true)
  echo "LOCAL_SYNTH_ANCHORS=$C"
  [ "$C" = 1 ] || exit 42
  awk -v SNIP="$HELP" '
    BEGIN{done=0}
    {
      if($0=="local_synthesize_takeover(){" && !done){
        while((getline x < SNIP)>0) print x
        close(SNIP)
        done=1
      }
      print
    }
    END{if(!done) exit 43}
  ' "$H" > "$HN" || exit 43
  echo "FRAME_OVERRIDE=INSERTED"
fi

# Add causal gate to the frame-degraded branch inside local_synthesize_takeover only.
if ! grep -Fq "FRAME_RECOVERY_CAUSAL_GATE_V1" "$HN"; then
  awk '
    BEGIN{inside=0; done=0}
    {
      if($0=="local_synthesize_takeover(){") inside=1
      print
      if(inside && !done && $0=="  if frame_degraded; then"){
        print "    # FRAME_RECOVERY_CAUSAL_GATE_V1"
        print "    if ! frame_recovery_boost_supported; then"
        print "      HDETAIL=local_frame_recovery_boost_not_supported_by_history"
        print "      return 1"
        print "    fi"
        done=1
      }
    }
    END{if(!done) exit 44}
  ' "$HN" > "$W/hermes.causal" || exit 44
  mv -f "$W/hermes.causal" "$HN"
fi

# Prevent a causality-rejected local boost from wasting a Cloud neuron.
if ! grep -Fq "FRAME_RECOVERY_CAUSAL_OBSERVE_BARRIER" "$HN"; then
  C=$(grep -c 'Gemini unavailable outside the local comfort path:' "$HN" 2>/dev/null || true)
  echo "CLOUD_BARRIER_ANCHORS=$C"
  [ "$C" = 1 ] || exit 45
  awk -v SNIP="$BARRIER" '
    BEGIN{done=0}
    {
      if(!done && index($0,"Gemini unavailable outside the local comfort path:")>0){
        while((getline x < SNIP)>0) print x
        close(SNIP)
        done=1
      }
      print
    }
    END{if(!done) exit 46}
  ' "$HN" > "$W/hermes.barrier" || exit 46
  mv -f "$W/hermes.barrier" "$HN"
fi

# Shadow hygiene: reset contextual metadata at the start of every evaluation cycle.
if grep -Fq "SHADOW_CONTEXT_RESET_V1" "$S"; then
  cp "$S" "$SN" || exit 47
else
  C=$(grep -c '^  DIGEST=NA; WINDOWS=0;' "$S" 2>/dev/null || true)
  echo "SHADOW_RESET_ANCHORS=$C"
  [ "$C" = 1 ] || exit 48
  awk '
    {
      print
      if(index($0,"  DIGEST=NA; WINDOWS=0;")==1 && !done){
        print "  # SHADOW_CONTEXT_RESET_V1"
        print "  CONTEXT_TIER=NONE; CONTEXT_HOURS=0; METRICS_RAW=NA"
        done=1
      }
    }
    END{if(!done) exit 49}
  ' "$S" > "$SN" || exit 49
fi

if sh -n "$HN"; then echo "HERMES_CANDIDATE_SYNTAX=OK"; else exit 51; fi
if sh -n "$SN"; then echo "SHADOW_CANDIDATE_SYNTAX=OK"; else exit 52; fi

for MARK in \
  FRAME_RECOVERY_LOCAL_BEFORE_CLOUD \
  CONTEXTUAL_HEALTHY_FRAME_OVERRIDE_V1 \
  FRAME_RECOVERY_CAUSAL_GATE_V1 \
  FRAME_RECOVERY_CAUSAL_OBSERVE_BARRIER \
  MULTI_REJECT_ALTERNATIVE_SYNTH \
  REJECT_QUARANTINE_NO_CLOUD
do
  grep -Fq "$MARK" "$HN" || { echo "$MARK=MISSING"; exit 53; }
  echo "$MARK=OK"
done

for MARK in \
  CONTEXTUAL_SHADOW_V4_RANGEFIX \
  CONTEXTUAL_SHADOW_V3_PARSEFIX \
  SHADOW_CONTEXT_RESET_V1
do
  grep -Fq "$MARK" "$SN" || { echo "$MARK=MISSING"; exit 54; }
  echo "$MARK=OK"
done

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_contextual_frame_causality.$TS" || exit 61
cp "$S" "$R/runtime/shadow.pre_contextual_frame_causality.$TS" || exit 62
cp "$HN" "$H" || exit 63
cp "$SN" "$S" || exit 64
chmod 755 "$H" "$S"

for N in hermes_adapter shadow; do
  P=$(cat "$R/runtime/locks/$N.lock/pid" 2>/dev/null)
  case "$P" in
    ""|*[!0-9]*) ;;
    *)
      kill -TERM "$P" 2>/dev/null
      sleep 1
      kill -0 "$P" 2>/dev/null && kill -KILL "$P" 2>/dev/null
      ;;
  esac
  rm -rf "$R/runtime/locks/$N.lock"
done

nohup sh "$H" "$R" "$M" >/dev/null 2>&1 &
nohup sh "$S" "$R" "$M" >/dev/null 2>&1 &

echo "PATCH=CONTEXTUAL_FRAME_CAUSALITY_V1_ACTIVE"
echo "HERMES_SYNTAX=OK"
echo "SHADOW_SYNTAX=OK"
