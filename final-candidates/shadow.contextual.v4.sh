#!/system/bin/sh
# Counterfactual shadow evaluator owned by AI Agent policy.
# Human-comfort objective is lexicographic: frame stability first, thermal comfort second, minimum power third.
# This worker never writes hardware.

ROOT="$1"
BIN_DIR="${0%/*}"
if [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim shadow
fi
HISTORY="$ROOT/history/telemetry.csv"
LEARN="$ROOT/history/learned_envelope.env"
POLICY="$ROOT/policy/candidate.env"
SNAP="$ROOT/runtime/snapshot.env"
OUT="$ROOT/runtime/shadow.env"
APPROVAL="$ROOT/policy/approved.env"
REJECT_LEDGER="$ROOT/history/shadow_reject_strategy.env"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }

publish(){
  _state="$1"; _reason="$2"; _now="$(date +%s)"
  t="$OUT.tmp.$$"
  {
    echo "SHADOW_STATE=$_state"
    echo "SHADOW_REASON=$_reason"
    echo "CANDIDATE_DIGEST=${DIGEST:-NA}"
    echo "SHADOW_WINDOWS=${WINDOWS:-0}"
    echo "SHADOW_FPS_AVG=${FPS_AVG:-NA}"
    echo "SHADOW_JANK_AVG=${JANK_AVG:-NA}"
    echo "SHADOW_P95_AVG=${P95_AVG:-NA}"
    echo "SHADOW_POWER_AVG_MW=${POWER_AVG:-NA}"
    echo "SHADOW_POWER_WINDOWS=${POWER_N:-0}"
    echo "SHADOW_CONTEXT_TIER=${CONTEXT_TIER:-NONE}"
    echo "SHADOW_CONTEXT_HOURS=${CONTEXT_HOURS:-0}"
    echo "SHADOW_METRICS_RAW=${METRICS_RAW:-NA}"
    echo "UPDATED_AT=$_now"
  } > "$t"
  chmod 600 "$t"; mv -f "$t" "$OUT"

  # PERSIST_REJECT_STRATEGY_MULTI
  case "$_reason" in
    human_comfort_contract_failed_*)
      _mf="$ROOT/history/shadow_reject_strategies.csv"
      if [ ! -r "$_mf" ]; then
        echo "AT,PACKAGE,INTENT,ACTUATORS,LITTLE_MIN_KHZ,LITTLE_MAX_KHZ,BIG_MIN_KHZ,BIG_MAX_KHZ,GPU_MIN_HZ,GPU_MAX_HZ,REASON" > "$_mf"
        chmod 600 "$_mf"
      fi
      _mp=$(kv PACKAGE "$POLICY")
      _mi=$(kv INTENT "$POLICY")
      _ma=$(kv ACTUATORS "$POLICY")
      # MULTIACTUATOR_PERSIST_NORMALIZE
      _ma=$(printf "%s" "$_ma" | tr ',' '+')
      _ml0=$(kv LITTLE_MIN_KHZ "$POLICY"); _ml1=$(kv LITTLE_MAX_KHZ "$POLICY")
      _mb0=$(kv BIG_MIN_KHZ "$POLICY"); _mb1=$(kv BIG_MAX_KHZ "$POLICY")
      _mg0=$(kv GPU_MIN_HZ "$POLICY"); _mg1=$(kv GPU_MAX_HZ "$POLICY")
      if ! awk -F, -v now="$_now" -v p="$_mp" -v i="$_mi" -v a="$_ma" \
        -v l0="$_ml0" -v l1="$_ml1" -v b0="$_mb0" -v b1="$_mb1" -v g0="$_mg0" -v g1="$_mg1" '
        NR>1 && $1~/^[0-9]+$/ && now-$1>=0 && now-$1<=900 &&
        $2==p && $3==i && $4==a && $5==l0 && $6==l1 &&
        $7==b0 && $8==b1 && $9==g0 && $10==g1 {found=1}
        END{exit !found}
      ' "$_mf" 2>/dev/null; then
        printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
          "$_now" "$_mp" "$_mi" "$_ma" "$_ml0" "$_ml1" \
          "$_mb0" "$_mb1" "$_mg0" "$_mg1" "$_reason" >> "$_mf"
      fi
      _mt="$_mf.tmp.$"
      {
        head -n 1 "$_mf"
        tail -n +2 "$_mf" | tail -n 64
      } > "$_mt"
      chmod 600 "$_mt"
      mv -f "$_mt" "$_mf"
      ;;
  esac

  # PERSIST_REJECT_STRATEGY
  if [ "$_state" = REJECT ] && [ -r "$POLICY" ]; then
    _rt="$REJECT_LEDGER.tmp.$"
    {
      echo "AT=$_now"
      echo "PACKAGE=$(kv PACKAGE "$POLICY")"
      echo "INTENT=$(kv INTENT "$POLICY")"
      echo "ACTUATORS=$(kv ACTUATORS "$POLICY")"
      echo "LITTLE_MIN_KHZ=$(kv LITTLE_MIN_KHZ "$POLICY")"
      echo "LITTLE_MAX_KHZ=$(kv LITTLE_MAX_KHZ "$POLICY")"
      echo "BIG_MIN_KHZ=$(kv BIG_MIN_KHZ "$POLICY")"
      echo "BIG_MAX_KHZ=$(kv BIG_MAX_KHZ "$POLICY")"
      echo "GPU_MIN_HZ=$(kv GPU_MIN_HZ "$POLICY")"
      echo "GPU_MAX_HZ=$(kv GPU_MAX_HZ "$POLICY")"
      echo "REASON=$_reason"
    } > "$_rt"
    chmod 600 "$_rt"
    mv -f "$_rt" "$REJECT_LEDGER"
  fi


  if [ "$_state" = PASS ] && [ -r "$POLICY" ]; then
    _a="$APPROVAL.tmp.$$"
    {
      echo "SCHEMA=DJAEGER_EXEC_APPROVAL_V2"
      echo "AT=$_now"
      echo "EXPIRES_AT=$((_now+120))"
      echo "EXECUTOR_ALLOWED=YES"
      echo "PACKAGE=$(kv PACKAGE "$POLICY")"
      echo "INTENT=$(kv INTENT "$POLICY")"
      echo "ACTUATORS=$(kv ACTUATORS "$POLICY")"
      echo "CANDIDATE_DIGEST=$(kv CANDIDATE_DIGEST "$POLICY")"
      echo "LITTLE_MIN_KHZ=$(kv LITTLE_MIN_KHZ "$POLICY")"
      echo "LITTLE_MAX_KHZ=$(kv LITTLE_MAX_KHZ "$POLICY")"
      echo "BIG_MIN_KHZ=$(kv BIG_MIN_KHZ "$POLICY")"
      echo "BIG_MAX_KHZ=$(kv BIG_MAX_KHZ "$POLICY")"
      echo "GPU_MIN_HZ=$(kv GPU_MIN_HZ "$POLICY")"
      echo "GPU_MAX_HZ=$(kv GPU_MAX_HZ "$POLICY")"
      echo "AUTHORITY=AI_AGENT_LOCAL_CONTROLLER"
      echo "OBJECTIVE=HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD"
    } > "$_a"
    chmod 600 "$_a"; mv -f "$_a" "$APPROVAL"
  else
    rm -f "$APPROVAL"
  fi
}

while true; do
  DIGEST=NA; WINDOWS=0; FPS_AVG=NA; JANK_AVG=NA; P95_AVG=NA; POWER_AVG=NA; POWER_N=0
  # SHADOW_CONTEXT_RESET_V1
  CONTEXT_TIER=NONE; CONTEXT_HOURS=0; METRICS_RAW=NA
  [ -r "$HISTORY" ] && [ -r "$LEARN" ] || { publish WAITING history_or_learning_missing; sleep 30; continue; }
  [ -r "$POLICY" ] || { publish WAITING candidate_missing; sleep 10; continue; }
  [ "$(kv VERDICT "$POLICY")" = PROPOSED ] || { publish WAITING candidate_not_proposed; sleep 10; continue; }
  [ "$(kv EXECUTOR_ENABLED "$POLICY")" = 0 ] || { publish REJECT candidate_must_not_self_enable; sleep 20; continue; }

  DIGEST=$(kv CANDIDATE_DIGEST "$POLICY"); PKG=$(kv PACKAGE "$POLICY")
  _approved_digest="$(kv CANDIDATE_DIGEST "$APPROVAL")"
  if [ -n "$_approved_digest" ] && [ "$_approved_digest" != "$DIGEST" ]; then
    rm -f "$APPROVAL"
  fi
  CANDIDATE_AT=$(kv AT "$POLICY"); case "$CANDIDATE_AT" in ''|*[!0-9]*) publish REJECT candidate_time_invalid; sleep 20; continue;; esac
  NOW=$(date +%s); AGE=$((NOW-CANDIDATE_AT))
  [ "$AGE" -ge 0 ] && [ "$AGE" -le 900 ] || { publish REJECT candidate_stale; sleep 20; continue; }
  # CONTEXTUAL_SHADOW_V2
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

    # CONTEXTUAL_SHADOW_V3_PARSEFIX
    METRICS_RAW="$METRICS"
    WINDOWS=$(printf "%s\n" "$METRICS" | awk '{print $1}')
    FPS_AVG=$(printf "%s\n" "$METRICS" | awk '{print $2}')
    JANK_AVG=$(printf "%s\n" "$METRICS" | awk '{print $3}')
    P95_AVG=$(printf "%s\n" "$METRICS" | awk '{print $4}')
    POWER_AVG=$(printf "%s\n" "$METRICS" | awk '{print $5}')
    POWER_N=$(printf "%s\n" "$METRICS" | awk '{print $6}')
    case "$WINDOWS" in ""|*[!0-9]*) WINDOWS=0;; esac
    case "$POWER_N" in ""|*[!0-9]*) POWER_N=0;; esac

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


  INTENT=$(kv INTENT "$POLICY"); [ -n "$INTENT" ] || INTENT=FRAME_FIRST_BALANCED
  BASE_FPS=$(kv FPS_P50 "$LEARN"); BASE_JANK=$(kv JANK_P95 "$LEARN"); BASE_P95=$(kv FRAME_P95_P95_MS "$LEARN")
  BASE_POWER50=$(kv POWER_P50_MW "$LEARN"); BASE_POWER95=$(kv POWER_P95_MW "$LEARN")
  case "$BASE_FPS:$BASE_JANK:$BASE_P95:$BASE_POWER50:$BASE_POWER95" in *[!0-9.:]*|:*) publish WAITING baseline_metric_missing; sleep 20; continue;; esac
  CUR_SKIN=$(kv SKIN_TEMP_C "$SNAP"); case "$CUR_SKIN" in ''|NA|*[!0-9.]*) CUR_SKIN=0;; esac
  COMFORT_PRESSURE=0
  awk -v s="$CUR_SKIN" 'BEGIN{exit !(s>0&&s>=42)}' && COMFORT_PRESSURE=1
  if awk -v intent="$INTENT" -v comfort="$COMFORT_PRESSURE" -v f="$FPS_AVG" -v bf="$BASE_FPS" -v j="$JANK_AVG" -v bj="$BASE_JANK" -v p="$P95_AVG" -v bp="$BASE_P95" -v w="$POWER_AVG" -v p50="$BASE_POWER50" -v p95="$BASE_POWER95" 'BEGIN{
    frame_ok=(bf>0&&bp>0&&f>=bf*0.98&&p<=bp*1.05&&((bj<=0&&j<=1)||(bj>0&&j<=bj*1.05)));
    frame_better=(f>=bf*1.02)||(p<=bp*0.95)||((bj>0)&&(j<=bj*0.85));
    if(intent=="FRAME_RECOVERY") ok=frame_ok&&frame_better&&(p95>0&&w<=p95*1.10);
    else if(intent=="POWER_EFFICIENCY") ok=frame_ok&&(p50>0&&w<=p50*1.05);
    else ok=frame_ok&&((frame_better&&(p95>0&&w<=p95*1.10))||(!frame_better&&(p50>0&&w<=p50*1.05)));
    if(comfort==1 && intent!="FRAME_RECOVERY") ok=ok&&(p50>0&&w<=p50);
    exit !ok
  }'; then
    if [ "$COMFORT_PRESSURE" = 1 ]; then
      publish PASS "human_comfort_frame_stable_thermal_pressure_power_reduced_${INTENT}"
    else
      publish PASS "human_comfort_frame_first_minimum_power_${INTENT}"
    fi
  else
    publish REJECT "human_comfort_contract_failed_${INTENT}"
  fi
  # Re-evaluate a live candidate promptly without busy-looping over history.
  sleep 20
done
