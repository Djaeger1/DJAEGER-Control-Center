#!/system/bin/sh
# Counterfactual shadow evaluator owned by AI Agent policy.
# Objective is lexicographic: frame stability first, minimum power second.
# This worker never writes hardware.

ROOT="$1"
HISTORY="$ROOT/history/telemetry.csv"
LEARN="$ROOT/history/learned_envelope.env"
POLICY="$ROOT/policy/candidate.env"
OUT="$ROOT/runtime/shadow.env"
APPROVAL="$ROOT/policy/approved.env"

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
    echo "UPDATED_AT=$_now"
  } > "$t"
  chmod 600 "$t"; mv -f "$t" "$OUT"

  if [ "$_state" = PASS ] && [ -r "$POLICY" ]; then
    _a="$APPROVAL.tmp.$$"
    {
      echo "SCHEMA=DJAEGER_EXEC_APPROVAL_V2"
      echo "AT=$_now"
      echo "EXPIRES_AT=$((_now+120))"
      echo "EXECUTOR_ALLOWED=YES"
      echo "PACKAGE=$(kv PACKAGE "$POLICY")"
      echo "CANDIDATE_DIGEST=$(kv CANDIDATE_DIGEST "$POLICY")"
      echo "LITTLE_MIN_KHZ=$(kv LITTLE_MIN_KHZ "$POLICY")"
      echo "LITTLE_MAX_KHZ=$(kv LITTLE_MAX_KHZ "$POLICY")"
      echo "BIG_MIN_KHZ=$(kv BIG_MIN_KHZ "$POLICY")"
      echo "BIG_MAX_KHZ=$(kv BIG_MAX_KHZ "$POLICY")"
      echo "GPU_MIN_HZ=$(kv GPU_MIN_HZ "$POLICY")"
      echo "GPU_MAX_HZ=$(kv GPU_MAX_HZ "$POLICY")"
      echo "AUTHORITY=AI_AGENT_LOCAL_CONTROLLER"
      echo "OBJECTIVE=FRAME_STABILITY_FIRST_MINIMUM_POWER_SECOND"
    } > "$_a"
    chmod 600 "$_a"; mv -f "$_a" "$APPROVAL"
  else
    rm -f "$APPROVAL"
  fi
}

while true; do
  DIGEST=NA; WINDOWS=0; FPS_AVG=NA; JANK_AVG=NA; P95_AVG=NA; POWER_AVG=NA; POWER_N=0
  [ -r "$POLICY" ] && [ -r "$HISTORY" ] && [ -r "$LEARN" ] || { publish WAITING candidate_or_history_missing; sleep 60; continue; }
  [ "$(kv VERDICT "$POLICY")" = PROPOSED ] || { publish WAITING candidate_not_proposed; sleep 60; continue; }
  [ "$(kv EXECUTOR_ENABLED "$POLICY")" = 0 ] || { publish REJECT candidate_must_not_self_enable; sleep 60; continue; }

  DIGEST=$(kv CANDIDATE_DIGEST "$POLICY"); PKG=$(kv PACKAGE "$POLICY")
  CANDIDATE_AT=$(kv AT "$POLICY"); case "$CANDIDATE_AT" in ''|*[!0-9]*) publish REJECT candidate_time_invalid; sleep 60; continue;; esac
  NOW=$(date +%s); AGE=$((NOW-CANDIDATE_AT))
  [ "$AGE" -ge 0 ] && [ "$AGE" -le 900 ] || { publish REJECT candidate_stale; sleep 60; continue; }
  CUTOFF=$((NOW-86400))
  LMIN=$(kv LITTLE_MIN_KHZ "$POLICY"); LMAX=$(kv LITTLE_MAX_KHZ "$POLICY")
  BMIN=$(kv BIG_MIN_KHZ "$POLICY"); BMAX=$(kv BIG_MAX_KHZ "$POLICY")
  GMIN=$(kv GPU_MIN_HZ "$POLICY"); GMAX=$(kv GPU_MAX_HZ "$POLICY")
  case "$LMIN:$LMAX:$BMIN:$BMAX:$GMIN:$GMAX" in *[!0-9:]*|:*) publish REJECT invalid_candidate; sleep 60; continue;; esac

  METRICS=$(awk -F, -v p="$PKG" -v cutoff="$CUTOFF" -v l0="$LMIN" -v l1="$LMAX" -v b0="$BMIN" -v b1="$BMAX" -v g0="$GMIN" -v g1="$GMAX" '
    NR>1 && $1+0>=cutoff && $3==p && $23=="STOCK_BASELINE" && $20+0>=20 && $21~/^[0-9]+$/ && !seen[$21]++ &&
    $7+0>=l0 && $7+0<=l1 && $8+0>=b0 && $8+0<=b1 && $9+0>=g0 && $9+0<=g1 &&
    $16~/^[0-9]+([.][0-9]+)?$/ && $17~/^[0-9]+([.][0-9]+)?$/ && $18~/^[0-9]+([.][0-9]+)?$/ {
      n++; fps+=$16; jank+=$17; p95+=$18
      if($14~/^[0-9]+([.][0-9]+)?$/ && $14+0>0){pn++; power+=$14}
    }
    END{
      if(n>0) printf "%d %.3f %.3f %.3f ",n,fps/n,jank/n,p95/n; else printf "0 0 0 0 "
      if(pn>0) printf "%.3f %d",power/pn,pn; else printf "0 0"
    }' "$HISTORY" 2>/dev/null)
  set -- $METRICS
  WINDOWS=${1:-0}; FPS_AVG=${2:-0}; JANK_AVG=${3:-0}; P95_AVG=${4:-0}; POWER_AVG=${5:-0}; POWER_N=${6:-0}
  [ "$WINDOWS" -ge 60 ] 2>/dev/null || { publish WAITING insufficient_matching_frame_windows; sleep 60; continue; }
  [ "$POWER_N" -ge 20 ] 2>/dev/null || { publish WAITING insufficient_power_evidence; sleep 60; continue; }

  BASE_FPS=$(kv FPS_P50 "$LEARN"); BASE_JANK=$(kv JANK_P95 "$LEARN"); BASE_P95=$(kv FRAME_P95_P95_MS "$LEARN"); BASE_POWER=$(kv POWER_P95_MW "$LEARN")
  case "$BASE_FPS:$BASE_JANK:$BASE_P95:$BASE_POWER" in *[!0-9.:]*|:*) publish WAITING baseline_metric_missing; sleep 60; continue;; esac
  if awk -v f="$FPS_AVG" -v bf="$BASE_FPS" -v j="$JANK_AVG" -v bj="$BASE_JANK" -v p="$P95_AVG" -v bp="$BASE_P95" -v w="$POWER_AVG" -v bw="$BASE_POWER" 'BEGIN{
    frame_ok=(bf>0&&bp>0&&f>=bf*0.98&&p<=bp*1.05&&((bj<=0&&j<=1)||(bj>0&&j<=bj*1.05)));
    frame_better=(p<=bp*0.95)||((bj>0)&&(j<=bj*0.85));
    power_ok=(bw>0)&&(w<=bw || (frame_better && w<=bw*1.10));
    ok=frame_ok&&power_ok;
    exit !ok
  }'; then
    publish PASS frame_priority_then_minimum_power
  else
    publish REJECT frame_first_contract_failed
  fi
  sleep 60
done
