#!/system/bin/sh

# ONE HERMES deputy runtime.
# Gemini is the primary/highest brain. Hermes Local + Hermes Cloud are ONE HERMES:
# one deputy identity with local continuity and on-demand cloud cognition.
# Hermes Cloud is neuron-guarded and escalated only when Gemini is unavailable,
# frame evidence is degraded, and local continuity has no proven safe strategy.
# No cloud path has hardware-write authority.

ROOT="$1"
BIN_DIR="${0%/*}"
if [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim hermes_adapter
fi
if [ -r "$BIN_DIR/neuron_accounting.sh" ]; then
  . "$BIN_DIR/neuron_accounting.sh"
fi
SNAP="$ROOT/runtime/snapshot.env"
WORKLOAD="$ROOT/runtime/workload.env"
LEARN="$ROOT/history/learned_envelope.env"
GEM="$ROOT/policy/gemini_proposal.env"
LOCAL_OUT="$ROOT/policy/hermes_local_vote.env"
CLOUD_OUT="$ROOT/policy/hermes_cloud_vote.env"
STATE="$ROOT/runtime/hermes_adapter.env"
LAST="$ROOT/config/hermes_review_last.env"
CLOUD_LAST="$ROOT/runtime/hermes_cloud_last_success.env"
GSTATE="$ROOT/runtime/gemini_reasoner.env"
HPLAN="$ROOT/policy/hermes_proposal.env"
OUTCOMES="$ROOT/history/outcomes.csv"
EXECUTION="$ROOT/runtime/execution.env"
NEURON="$ROOT/config/hermes_neuron_live.env"
CLOUD_MIN_INTERVAL=900
CLOUD_BOOT_GUARD_SEC=120
HERMES_BOOT_AT=$(date +%s)

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
num(){ case "$1" in ''|*[!0-9.-]*) echo 0;; *) echo "$1";; esac; }
clean(){ printf '%s' "$1" | tr '\r\n\t' '   ' | tr -cd 'A-Za-z0-9._:+/%=,@ -' | cut -c1-120; }

digest(){
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" 2>/dev/null | awk '{print $1}'
  else cksum "$1" 2>/dev/null | awk '{print $1}'
  fi
}

contains_freq(){
  value="$1"; list="$2"
  case "$value" in ''|*[!0-9]*) return 1;; esac
  for x in $list; do [ "$x" = "$value" ] && return 0; done
  return 1
}

json_escape(){
  LC_ALL=C printf '%s' "$1" | tr -d '\000-\010\013-\037' | tr '\011' ' ' | sed 's/\\/\\\\/g;s/"/\\"/g' | awk 'BEGIN{ORS=""}{if(NR>1)printf "\\n";printf "%s",$0}'
}

config_value(){
  key="$1"
  for f in "$ROOT/config/hermes_cloud.env" "$ROOT/config/identity.env"; do
    [ -r "$f" ] || continue
    sed -n "s/^[[:space:]]*$key[[:space:]]*=[[:space:]]*['\"]\{0,1\}\([^'\"[:space:]]\{4,\}\).*/\1/p" "$f" 2>/dev/null | head -n1
  done | head -n1
}

write_state(){
  t="$STATE.tmp.$$"
  {
    echo "HERMES_ADAPTER_STATE=$1"
    echo "HERMES_LOCAL_STATE=${HLOCAL_STATE:-WAITING}"
    echo "HERMES_CLOUD_STATE=${HCLOUD_STATE:-STANDBY}"
    echo "HERMES_CLOUD_DETAIL=$(clean "${HDETAIL:-no_review_yet}")"
    echo "HERMES_CLOUD_HTTP=${HTTP:-NA}"
    echo "HERMES_CLOUD_ROUTE=${HROUTE:-LOCAL}"
    echo "HERMES_CLOUD_MODEL=${HMODEL:-NA}"
    echo "HERMES_CLOUD_AUTH=${HAUTH:-UNKNOWN}"
    echo "HERMES_MODE=${HMODE:-DEPUTY_STANDBY}"
    echo "HERMES_ACTIVE_SOURCE=${HACTIVE_SOURCE:-NONE}"
    _cl_at="$(kv AT "$CLOUD_LAST")"; case "$_cl_at" in ''|*[!0-9]*) _cl_at=0;; esac
    _cl_route="$(kv ROUTE "$CLOUD_LAST")"; [ -n "$_cl_route" ] || _cl_route=NA
    _cl_model="$(kv MODEL "$CLOUD_LAST")"; [ -n "$_cl_model" ] || _cl_model=NA
    _cl_verdict="$(kv VERDICT "$CLOUD_LAST")"; [ -n "$_cl_verdict" ] || _cl_verdict=NA
    _cl_http="$(kv HTTP "$CLOUD_LAST")"; [ -n "$_cl_http" ] || _cl_http=NA
    _cl_delta="$(kv NEURON_DELTA "$CLOUD_LAST")"; [ -n "$_cl_delta" ] || _cl_delta=0
    _cl_used=NO
    if [ "$_cl_at" -gt 0 ] 2>/dev/null; then
      _cl_used=YES
    else
      _ledger_calls=$(num "$(kv SUCCESS_CALLS "$NEURON")")
      _ledger_at="$(kv UPDATED_AT "$NEURON")"; case "$_ledger_at" in ''|*[!0-9]*) _ledger_at=0;; esac
      if [ "$_ledger_calls" -gt 0 ] 2>/dev/null && [ "$_ledger_at" -gt 0 ] 2>/dev/null; then
        _cl_at="$_ledger_at"
        _cl_used=YES
        _cl_route=UNRECORDED_PRE_PERSISTENCE
        _cl_model=UNRECORDED_PRE_PERSISTENCE
        _cl_verdict=UNRECORDED_PRE_PERSISTENCE
        _cl_http=200
        _cl_delta="$(kv LAST_DELTA "$NEURON")"; [ -n "$_cl_delta" ] || _cl_delta=0
      fi
    fi
    _cl_age=$(( $(date +%s) - _cl_at )); [ "$_cl_age" -ge 0 ] 2>/dev/null || _cl_age=999999
    echo "HERMES_CLOUD_USED=$_cl_used"
    echo "HERMES_CLOUD_ACTIVE=$([ "${HACTIVE_SOURCE:-NONE}" = HERMES_CLOUD ] && echo YES || echo NO)"
    echo "HERMES_CLOUD_LAST_SUCCESS_AT=$_cl_at"
    echo "HERMES_CLOUD_LAST_SUCCESS_AGE_SEC=$_cl_age"
    echo "HERMES_CLOUD_LAST_ROUTE=$_cl_route"
    echo "HERMES_CLOUD_LAST_MODEL=$_cl_model"
    echo "HERMES_CLOUD_LAST_VERDICT=$_cl_verdict"
    echo "HERMES_CLOUD_LAST_HTTP=$_cl_http"
    echo "HERMES_CLOUD_LAST_NEURON_DELTA=$_cl_delta"
    echo "HERMES_CLOUD_POLICY=ON_DEMAND_NEURON_GUARDED"
    echo "PRIMARY_BRAIN=GEMINI"
    echo "DEPUTY_BRAIN=HERMES_H2"
    echo "ONE_HERMES=LOCAL_PLUS_CLOUD_ONE_IDENTITY"
    echo "OBJECTIVE=HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD"
    echo "UPDATED_AT=$(date +%s)"
  } > "$t"
  chmod 600 "$t"; mv -f "$t" "$STATE"
}

cloud_probe(){
  token=$(config_value HERMES_ACCESS_KEY)
  if [ -z "$token" ]; then
    HAUTH=NOT_CONFIGURED
    HCLOUD_STATE=NO_KEY
    HDETAIL=hermes_access_key_not_found
    HTTP=NA
    HROUTE=LOCAL
    HMODEL=NA
    return 1
  fi
  HAUTH=CONFIGURED_UNVERIFIED
  endpoint=$(config_value HERMES_ENDPOINT); [ -n "$endpoint" ] || endpoint=$(config_value ENDPOINT)
  [ -n "$endpoint" ] || endpoint=https://hermes-cloud-djaeger.moclomper.workers.dev
  case "$endpoint" in
    */v1/chat) base="${endpoint%/v1/chat}" ;;
    */chat) base="${endpoint%/chat}" ;;
    *) base="${endpoint%/}" ;;
  esac
  command -v curl >/dev/null 2>&1 || {
    HCLOUD_STATE=UNAVAILABLE; HDETAIL=curl_missing; HTTP=NA; HROUTE=LOCAL; HMODEL=NA; unset token; return 1;
  }
  HTTP=$(curl --http1.1 --connect-timeout 4 -m 8 -sS -o /dev/null -w '%{http_code}' "$base/health" 2>/dev/null)
  unset token
  case "$HTTP" in
    200) HCLOUD_STATE=REACHABLE_IDLE; HDETAIL=cloud_health_reachable_auth_unverified; HROUTE=LOCAL; HMODEL=NA; return 0 ;;
    401|403) HCLOUD_STATE=REACHABLE_IDLE; HDETAIL="health_endpoint_auth_policy_$HTTP"; HROUTE=LOCAL; HMODEL=NA; return 0 ;;
    *) HCLOUD_STATE=HTTP_ERROR; HDETAIL="cloud_health_${HTTP:-000}"; HROUTE=LOCAL; HMODEL=NA; return 1 ;;
  esac
}

local_validate(){
  HLOCAL_STATE=REJECTED
  [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" = GAME ] || { HDETAIL=non_game_workload; return 1; }
  [ "$(kv PACKAGE "$WORKLOAD")" = "$(kv PACKAGE "$GEM")" ] || { HDETAIL=active_workload_mismatch; return 1; }
  [ "$(kv PACKAGE "$GEM")" = "$(kv PACKAGE "$LEARN")" ] || { HDETAIL=context_mismatch; return 1; }
  [ "$(kv STATE "$LEARN")" = READY_HARDWARE_MODEL ] || { HDETAIL=baseline_not_mature; return 1; }
  [ "$(kv FRAME_EVIDENCE "$LEARN")" = VALID ] || { HDETAIL=frame_baseline_not_mature; return 1; }

  glmin=$(kv LITTLE_MIN_KHZ "$GEM"); glmax=$(kv LITTLE_MAX_KHZ "$GEM")
  gbmin=$(kv BIG_MIN_KHZ "$GEM"); gbmax=$(kv BIG_MAX_KHZ "$GEM")
  ggmin=$(kv GPU_MIN_HZ "$GEM"); ggmax=$(kv GPU_MAX_HZ "$GEM")
  lmin=$(kv LITTLE_MIN_KHZ "$LEARN"); lmax=$(kv LITTLE_MAX_KHZ "$LEARN")
  bmin=$(kv BIG_MIN_KHZ "$LEARN"); bmax=$(kv BIG_MAX_KHZ "$LEARN")
  gmin=$(kv GPU_MIN_HZ "$LEARN"); gmax=$(kv GPU_MAX_HZ "$LEARN")
  case "$glmin:$glmax:$gbmin:$gbmax:$ggmin:$ggmax:$lmin:$lmax:$bmin:$bmax:$gmin:$gmax" in
    *[!0-9:]*) HDETAIL=non_numeric_candidate; return 1;;
  esac
  [ "$glmin" -ge "$lmin" ] && [ "$glmax" -le "$lmax" ] && [ "$glmin" -le "$glmax" ] || { HDETAIL=little_outside_measured_envelope; return 1; }
  [ "$gbmin" -ge "$bmin" ] && [ "$gbmax" -le "$bmax" ] && [ "$gbmin" -le "$gbmax" ] || { HDETAIL=big_outside_measured_envelope; return 1; }
  [ "$ggmin" -ge "$gmin" ] && [ "$ggmax" -le "$gmax" ] && [ "$ggmin" -le "$ggmax" ] || { HDETAIL=gpu_outside_measured_envelope; return 1; }

  lav=$(kv LITTLE_AVAILABLE_KHZ "$SNAP"); bav=$(kv BIG_AVAILABLE_KHZ "$SNAP"); gav=$(kv GPU_AVAILABLE_HZ "$SNAP")
  contains_freq "$glmin" "$lav" && contains_freq "$glmax" "$lav" || { HDETAIL=unsupported_little_opp; return 1; }
  contains_freq "$gbmin" "$bav" && contains_freq "$gbmax" "$bav" || { HDETAIL=unsupported_big_opp; return 1; }
  contains_freq "$ggmin" "$gav" && contains_freq "$ggmax" "$gav" || { HDETAIL=unsupported_gpu_opp; return 1; }

  skin=$(num "$(kv SKIN_TEMP_C "$SNAP")"); bat=$(num "$(kv BATTERY_TEMP_C "$SNAP")"); cpu=$(num "$(kv CPU_TEMP_C "$SNAP")")
  awk -v s="$skin" -v b="$bat" -v c="$cpu" 'BEGIN{exit !((s<=0||s<46)&&(b<=0||b<45)&&(c<=0||c<75))}' || { HDETAIL=thermal_guard_active; return 1; }

  base_conf=$(kv CONFIDENCE "$LEARN"); case "$base_conf" in ''|*[!0-9]*) base_conf=75;; esac
  conf=$((base_conf+5)); [ "$conf" -gt 95 ] && conf=95
  d=$(digest "$GEM"); [ -n "$d" ] || { HDETAIL=digest_unavailable; return 1; }
  t="$LOCAL_OUT.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_HERMES_LOCAL_REVIEW_V1"
    echo "AT=$(date +%s)"
    echo "PACKAGE=$(kv PACKAGE "$GEM")"
    echo "VOTE=VALIDATE_CANDIDATE"
    echo "CONFIDENCE=$conf"
    echo "CANDIDATE_DIGEST=$d"
    echo "REASON=MEASURED_ENVELOPE_OPP_THERMAL_FRAME_GUARDS_PASS"
    echo "APPLY_AUTHORITY=NONE"
  } > "$t"
  chmod 600 "$t"; mv -f "$t" "$LOCAL_OUT"
  HLOCAL_STATE=VALIDATED_CANDIDATE
  HDETAIL=local_validation_pass
  return 0
}

cloud_review(){
  d=$(digest "$GEM"); [ -n "$d" ] || return 1
  token=$(config_value HERMES_ACCESS_KEY)
  [ -n "$token" ] || { rm -f "$CLOUD_OUT"; HAUTH=NOT_CONFIGURED; HCLOUD_STATE=NO_KEY; HDETAIL=hermes_access_key_not_found; return 1; }
  HAUTH=CONFIGURED_UNVERIFIED
  old=$(kv CANDIDATE_DIGEST "$CLOUD_OUT")
  if [ "$old" = "$d" ]; then
    cached=$(kv VERDICT "$CLOUD_OUT")
    [ "$cached" = APPROVE ] && HCLOUD_STATE=APPROVED || HCLOUD_STATE=REJECTED
    HROUTE=$(kv ROUTE "$CLOUD_OUT"); [ -n "$HROUTE" ] || HROUTE=SMART
    HMODEL=$(kv MODEL "$CLOUD_OUT"); [ -n "$HMODEL" ] || HMODEL=NA
    HTTP=$(kv HTTP_CODE "$CLOUD_OUT"); [ -n "$HTTP" ] || HTTP=CACHED
    HDETAIL=cached_cloud_review
    unset token
    [ "$cached" = APPROVE ]
    return
  fi

  now=$(date +%s); last_at=$(kv AT "$LAST"); last_d=$(kv DIGEST "$LAST")
  case "$last_at" in ''|*[!0-9]*) last_at=0;; esac
  if [ "$last_d" = "$d" ] && [ $((now-last_at)) -lt 900 ]; then
    HCLOUD_STATE=COOLDOWN; HDETAIL=cloud_review_retry_guard; unset token; return 1
  fi

  endpoint=$(config_value HERMES_ENDPOINT); [ -n "$endpoint" ] || endpoint=$(config_value ENDPOINT)
  [ -n "$endpoint" ] || endpoint=https://hermes-cloud-djaeger.moclomper.workers.dev
  case "$endpoint" in */v1/chat|*/chat) url="$endpoint";; *) url="${endpoint%/}/v1/chat";; esac
  command -v curl >/dev/null 2>&1 || { HCLOUD_STATE=UNAVAILABLE; HDETAIL=curl_missing; unset token; return 1; }
  HROUTE=SMART

  pkg=$(kv PACKAGE "$GEM"); conf=$(kv CONFIDENCE "$GEM")
  glmin=$(kv LITTLE_MIN_KHZ "$GEM"); glmax=$(kv LITTLE_MAX_KHZ "$GEM")
  gbmin=$(kv BIG_MIN_KHZ "$GEM"); gbmax=$(kv BIG_MAX_KHZ "$GEM")
  ggmin=$(kv GPU_MIN_HZ "$GEM"); ggmax=$(kv GPU_MAX_HZ "$GEM")
  samples=$(kv SAMPLES "$LEARN"); frames=$(kv FRAME_WINDOWS "$LEARN")
  fps=$(kv FPS_P50 "$LEARN"); jank=$(kv JANK_P95 "$LEARN"); p95=$(kv FRAME_P95_P95_MS "$LEARN"); p99=$(kv FRAME_P99_P95_MS "$LEARN")
  message="Review one measured DJAEGER Observer candidate. Package=$pkg samples=$samples independent_frame_windows=$frames stock_fps_p50=$fps stock_jank_p95=$jank stock_p95=$p95 stock_p99=$p99 candidate_confidence=$conf candidate_little=$glmin-$glmax candidate_big=$gbmin-$gbmax candidate_gpu=$ggmin-$ggmax. The local validator already confirmed stock-envelope bounds, exact kernel OPP membership, thermal headroom, and frame maturity. Approve only when the candidate is conservative enough for offline shadow comparison. Return exactly: HERMES_REVIEW VERDICT=APPROVE_or_REJECT CONFIDENCE=0_to_100 REASON=short_token"
  system="You are ONE HERMES Cloud, an advisory reviewer. You have no root, sysfs, or execution authority. Do not return commands or paths."
  req="$ROOT/runtime/.hermes_request.$$"; resp="$ROOT/runtime/.hermes_response.$$"
  printf '{"mode":"SMART","task":"observer_review","message":"%s","prompt":"%s","system":"%s","fallback":false,"max_tokens":128,"temperature":0.1}' "$(json_escape "$message")" "$(json_escape "$message")" "$(json_escape "$system")" > "$req"
  chmod 600 "$req"
  curlcfg="$(mktemp "$ROOT/runtime/.hermes_curl.XXXXXX" 2>/dev/null)"; [ -n "$curlcfg" ] || { unset token; rm -f "$req"; HCLOUD_STATE=UNAVAILABLE; HDETAIL=tempfile_failed; return 1; }
  printf 'header = "Authorization: Bearer %s"\n' "$token" > "$curlcfg"
  chmod 600 "$curlcfg"
  HTTP=$(curl --http1.1 --connect-timeout 5 -m 15 -sS -o "$resp" -w '%{http_code}' -K "$curlcfg" -H 'Content-Type: application/json' --data-binary "@$req" "$url" 2>/dev/null)
  unset token
  rm -f "$curlcfg"
  if [ "$HTTP" = 200 ] && [ -r "$resp" ] && grep -Eq '"ok"[[:space:]]*:[[:space:]]*true|"text"[[:space:]]*:' "$resp" 2>/dev/null; then
    command -v neuron_record_success >/dev/null 2>&1 && neuron_record_success SMART "$req" "$resp"
  fi
  rm -f "$req"
  {
    echo "AT=$now"
    echo "DIGEST=$d"
  } > "$LAST.tmp.$$"; chmod 600 "$LAST.tmp.$$"; mv -f "$LAST.tmp.$$" "$LAST"
  if [ "$HTTP" = 401 ] || [ "$HTTP" = 403 ]; then HAUTH=AUTH_ERROR; HCLOUD_STATE=AUTH_ERROR; HDETAIL="cloud_auth_$HTTP"; rm -f "$resp"; return 1; fi
  [ "$HTTP" = 200 ] || { HCLOUD_STATE=HTTP_ERROR; HDETAIL="cloud_http_$HTTP"; rm -f "$resp"; return 1; }
  HAUTH=CONFIGURED

  verdict=$(grep -o 'VERDICT=\(APPROVE\|REJECT\)' "$resp" 2>/dev/null | tail -n1 | cut -d= -f2)
  hconf=$(grep -o 'CONFIDENCE=[0-9][0-9]*' "$resp" 2>/dev/null | tail -n1 | cut -d= -f2)
  reason=$(grep -o 'REASON=[A-Za-z0-9_.:-]*' "$resp" 2>/dev/null | tail -n1 | cut -d= -f2-)
  HROUTE=$(grep -o '"mode"[[:space:]]*:[[:space:]]*"[A-Z]*"' "$resp" 2>/dev/null | head -n1 | sed 's/.*"\([A-Z][A-Z]*\)"$/\1/')
  HMODEL=$(grep -o '"model"[[:space:]]*:[[:space:]]*"[^"]*"' "$resp" 2>/dev/null | head -n1 | sed 's/.*:[[:space:]]*"//;s/"$//')
  [ -n "$HROUTE" ] || HROUTE=SMART
  [ -n "$HMODEL" ] || HMODEL=NA
  rm -f "$resp"
  case "$hconf" in ''|*[!0-9]*) verdict=INVALID;; esac
  case "$verdict" in APPROVE|REJECT) :;; *) HCLOUD_STATE=INVALID; HDETAIL=unparseable_cloud_review; return 1;; esac
  [ "$hconf" -le 100 ] 2>/dev/null || { HCLOUD_STATE=INVALID; HDETAIL=invalid_cloud_confidence; return 1; }

  t="$CLOUD_OUT.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_HERMES_CLOUD_REVIEW_V1"
    echo "AT=$(date +%s)"
    echo "PACKAGE=$pkg"
    echo "VERDICT=$verdict"
    echo "VOTE=${verdict}_CANDIDATE"
    echo "CONFIDENCE=$hconf"
    echo "CANDIDATE_DIGEST=$d"
    echo "REASON=$(clean "${reason:-HERMES_CLOUD_REVIEW}")"
    echo "ROUTE=${HROUTE:-SMART}"
    echo "MODEL=${HMODEL:-NA}"
    echo "HTTP_CODE=${HTTP:-NA}"
    echo "APPLY_AUTHORITY=NONE"
  } > "$t"
  chmod 600 "$t"; mv -f "$t" "$CLOUD_OUT"
  [ "$verdict" = APPROVE ] && HCLOUD_STATE=APPROVED || HCLOUD_STATE=REJECTED
  HDETAIL="${reason:-cloud_review_complete}"
  [ "$verdict" = APPROVE ]
}


gemini_context_current(){
  [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" = GAME ] || return 1
  _wp=$(kv PACKAGE "$WORKLOAD")
  _gp=$(kv GEMINI_CONTEXT_PACKAGE "$GSTATE")
  _gc=$(kv GEMINI_CONTEXT_CLASS "$GSTATE")
  _ga=$(kv UPDATED_AT "$GSTATE"); case "$_ga" in ''|*[!0-9]*) return 1;; esac
  _gage=$(( $(date +%s) - _ga ))
  [ "$_gage" -ge 0 ] && [ "$_gage" -le 30 ] || return 1
  [ "$_gc" = GAME ] && [ -n "$_wp" ] && [ "$_gp" = "$_wp" ]
}

gemini_live(){
  gemini_context_current || return 1
  _gs=$(kv GEMINI_STATE "$GSTATE")
  case "$_gs" in CANDIDATE|OBSERVE|READY) return 0;; *) return 1;; esac
}

gemini_failed(){
  # Context-stale/mismatched primary is unavailable for the current game even
  # if its last state was READY/OBSERVE for another app.
  gemini_context_current || return 0
  _gs=$(kv GEMINI_STATE "$GSTATE")
  case "$_gs" in ALL_KEYS_COOLDOWN|AUTH_ERROR|HTTP_ERROR|NO_KEY|UNAVAILABLE) return 0;; *) return 1;; esac
}

frame_degraded(){
  _fps=$(num "$(kv FPS_EST "$SNAP")"); _jank=$(num "$(kv JANK_PCT "$SNAP")"); _p95=$(num "$(kv P95_MS "$SNAP")")
  _bfps=$(num "$(kv FPS_P50 "$LEARN")"); _bjank=$(num "$(kv JANK_P95 "$LEARN")"); _bp95=$(num "$(kv FRAME_P95_P95_MS "$LEARN")")
  awk -v f="$_fps" -v j="$_jank" -v p="$_p95" -v bf="$_bfps" -v bj="$_bjank" -v bp="$_bp95" 'BEGIN{
    if(bf<=0 || bp<=0) exit 1;
    bad=(f>0 && f<bf*0.98) || (p>0 && p>bp*1.08);
    if(j>=0 && bj>0 && j>bj*1.20+1) bad=1;
    exit bad?0:1
  }'
}

validate_candidate_file(){
  _src="$1"
  [ -r "$_src" ] || { HDETAIL=candidate_missing; return 1; }
  [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" = GAME ] || { HDETAIL=non_game_workload; return 1; }
  _pkg=$(kv PACKAGE "$_src")
  [ "$_pkg" = "$(kv PACKAGE "$WORKLOAD")" ] || { HDETAIL=active_workload_mismatch; return 1; }
  [ "$_pkg" = "$(kv PACKAGE "$LEARN")" ] || { HDETAIL=context_mismatch; return 1; }
  [ "$(kv STATE "$LEARN")" = READY_HARDWARE_MODEL ] || { HDETAIL=baseline_not_mature; return 1; }
  [ "$(kv FRAME_EVIDENCE "$LEARN")" = VALID ] || { HDETAIL=frame_baseline_not_mature; return 1; }

  _glmin=$(kv LITTLE_MIN_KHZ "$_src"); _glmax=$(kv LITTLE_MAX_KHZ "$_src")
  _gbmin=$(kv BIG_MIN_KHZ "$_src"); _gbmax=$(kv BIG_MAX_KHZ "$_src")
  _ggmin=$(kv GPU_MIN_HZ "$_src"); _ggmax=$(kv GPU_MAX_HZ "$_src")
  _lmin=$(kv LITTLE_MIN_KHZ "$LEARN"); _lmax=$(kv LITTLE_MAX_KHZ "$LEARN")
  _bmin=$(kv BIG_MIN_KHZ "$LEARN"); _bmax=$(kv BIG_MAX_KHZ "$LEARN")
  _gmin=$(kv GPU_MIN_HZ "$LEARN"); _gmax=$(kv GPU_MAX_HZ "$LEARN")
  case "$_glmin:$_glmax:$_gbmin:$_gbmax:$_ggmin:$_ggmax:$_lmin:$_lmax:$_bmin:$_bmax:$_gmin:$_gmax" in
    *[!0-9:]*) HDETAIL=non_numeric_candidate; return 1;;
  esac
  [ "$_glmin" -ge "$_lmin" ] && [ "$_glmax" -le "$_lmax" ] && [ "$_glmin" -le "$_glmax" ] || { HDETAIL=little_outside_measured_envelope; return 1; }
  [ "$_gbmin" -ge "$_bmin" ] && [ "$_gbmax" -le "$_bmax" ] && [ "$_gbmin" -le "$_gbmax" ] || { HDETAIL=big_outside_measured_envelope; return 1; }
  [ "$_ggmin" -ge "$_gmin" ] && [ "$_ggmax" -le "$_gmax" ] && [ "$_ggmin" -le "$_ggmax" ] || { HDETAIL=gpu_outside_measured_envelope; return 1; }

  _lav=$(kv LITTLE_AVAILABLE_KHZ "$SNAP"); _bav=$(kv BIG_AVAILABLE_KHZ "$SNAP"); _gav=$(kv GPU_AVAILABLE_HZ "$SNAP")
  contains_freq "$_glmin" "$_lav" && contains_freq "$_glmax" "$_lav" || { HDETAIL=unsupported_little_opp; return 1; }
  contains_freq "$_gbmin" "$_bav" && contains_freq "$_gbmax" "$_bav" || { HDETAIL=unsupported_big_opp; return 1; }
  contains_freq "$_ggmin" "$_gav" && contains_freq "$_ggmax" "$_gav" || { HDETAIL=unsupported_gpu_opp; return 1; }

  _skin=$(num "$(kv SKIN_TEMP_C "$SNAP")"); _bat=$(num "$(kv BATTERY_TEMP_C "$SNAP")"); _cpu=$(num "$(kv CPU_TEMP_C "$SNAP")"); _gpu_t=$(num "$(kv GPU_TEMP_C "$SNAP")")
  awk -v s="$_skin" -v b="$_bat" -v c="$_cpu" -v g="$_gpu_t" 'BEGIN{exit !((s<=0||s<46)&&(b<=0||b<45)&&(c<=0||c<75)&&(g<=0||g<75))}' || { HDETAIL=thermal_guard_active; return 1; }
  return 0
}

write_local_vote(){
  _src="$1"; _vote="$2"; _reason="$3"
  _d=$(digest "$_src"); [ -n "$_d" ] || return 1
  _base=$(kv CONFIDENCE "$LEARN"); case "$_base" in ''|*[!0-9]*) _base=75;; esac
  _conf=$((_base+5)); [ "$_conf" -gt 95 ] && _conf=95
  _t="$LOCAL_OUT.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_ONE_HERMES_LOCAL_V2"
    echo "AT=$(date +%s)"
    echo "PACKAGE=$(kv PACKAGE "$_src")"
    echo "VOTE=$_vote"
    echo "CONFIDENCE=$_conf"
    echo "CANDIDATE_DIGEST=$_d"
    echo "REASON=$_reason"
    echo "ROLE=DEPUTY_LOCAL_CONTINUITY"
    echo "APPLY_AUTHORITY=NONE"
  } > "$_t"
  chmod 600 "$_t"; mv -f "$_t" "$LOCAL_OUT"
}

write_hermes_plan(){
  _src="$1"; _source="$2"; _conf="$3"; _reason="$4"; _intent="$5"
  [ -n "$_intent" ] || _intent=FRAME_FIRST_BALANCED
  _actuators="$(kv ACTUATORS "$_src")"; [ -n "$_actuators" ] || _actuators=ALL

  # Keep the same plan file/digest stable while the strategy is unchanged.
  # Shadow/approval/executor bind to this digest, so needless AT rewrites would
  # continuously invalidate an otherwise valid candidate.
  _hat=$(kv AT "$HPLAN"); case "$_hat" in ''|*[!0-9]*) _hat=0;; esac
  _hage=$(( $(date +%s) - _hat )); [ "$_hage" -ge 0 ] 2>/dev/null || _hage=999999
  if [ -r "$HPLAN" ] && [ "$_hage" -le 900 ] 2>/dev/null &&
     [ "$(kv PACKAGE "$HPLAN")" = "$(kv PACKAGE "$_src")" ] &&
     [ "$(kv BRAIN_SOURCE "$HPLAN")" = "$_source" ] &&
     [ "$(kv INTENT "$HPLAN")" = "$_intent" ] &&
     [ "$(kv ACTUATORS "$HPLAN")" = "$_actuators" ] &&
     [ "$(kv REASON "$HPLAN")" = "$_reason" ] &&
     [ "$(kv LITTLE_MIN_KHZ "$HPLAN")" = "$(kv LITTLE_MIN_KHZ "$_src")" ] &&
     [ "$(kv LITTLE_MAX_KHZ "$HPLAN")" = "$(kv LITTLE_MAX_KHZ "$_src")" ] &&
     [ "$(kv BIG_MIN_KHZ "$HPLAN")" = "$(kv BIG_MIN_KHZ "$_src")" ] &&
     [ "$(kv BIG_MAX_KHZ "$HPLAN")" = "$(kv BIG_MAX_KHZ "$_src")" ] &&
     [ "$(kv GPU_MIN_HZ "$HPLAN")" = "$(kv GPU_MIN_HZ "$_src")" ] &&
     [ "$(kv GPU_MAX_HZ "$HPLAN")" = "$(kv GPU_MAX_HZ "$_src")" ]; then
    return 0
  fi

  _t="$HPLAN.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_ONE_HERMES_TAKEOVER_V1"
    echo "AT=$(date +%s)"
    echo "PACKAGE=$(kv PACKAGE "$_src")"
    echo "VERDICT=CANDIDATE"
    echo "CONFIDENCE=$_conf"
    echo "INTENT=$_intent"
    echo "ACTUATORS=$_actuators"
    echo "LITTLE_MIN_KHZ=$(kv LITTLE_MIN_KHZ "$_src")"
    echo "LITTLE_MAX_KHZ=$(kv LITTLE_MAX_KHZ "$_src")"
    echo "BIG_MIN_KHZ=$(kv BIG_MIN_KHZ "$_src")"
    echo "BIG_MAX_KHZ=$(kv BIG_MAX_KHZ "$_src")"
    echo "GPU_MIN_HZ=$(kv GPU_MIN_HZ "$_src")"
    echo "GPU_MAX_HZ=$(kv GPU_MAX_HZ "$_src")"
    echo "REASON=$_reason"
    echo "BRAIN_SOURCE=$_source"
    echo "BRAIN_ROLE=DEPUTY_TAKEOVER"
    echo "ONE_HERMES=LOCAL_PLUS_CLOUD_ONE_IDENTITY"
    echo "OBJECTIVE=HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD"
    echo "APPLY_AUTHORITY=NONE"
  } > "$_t"
  chmod 600 "$_t"; mv -f "$_t" "$HPLAN"
}

local_history_takeover(){
  [ -r "$OUTCOMES" ] || return 1
  _pkg=$(kv ACTIVE_PACKAGE "$SNAP")
  _line=$(awk -F, -v p="$_pkg" 'NR>1&&$2==p&&$4=="KEPT"{x=$0}END{print x}' "$OUTCOMES" 2>/dev/null)
  [ -n "$_line" ] || return 1
  _lr=$(printf '%s\n' "$_line" | cut -d, -f11)
  _br=$(printf '%s\n' "$_line" | cut -d, -f12)
  _gr=$(printf '%s\n' "$_line" | cut -d, -f13)
  _l0=$(printf '%s' "$_lr" | cut -d- -f1); _l1=$(printf '%s' "$_lr" | cut -d- -f2)
  _b0=$(printf '%s' "$_br" | cut -d- -f1); _b1=$(printf '%s' "$_br" | cut -d- -f2)
  _g0=$(printf '%s' "$_gr" | cut -d- -f1); _g1=$(printf '%s' "$_gr" | cut -d- -f2)
  case "$_l0:$_l1:$_b0:$_b1:$_g0:$_g1" in *[!0-9:]*) return 1;; esac
  _tmp="$ROOT/runtime/.hermes_local_candidate.$$"
  {
    echo "PACKAGE=$_pkg"
    echo "LITTLE_MIN_KHZ=$_l0"; echo "LITTLE_MAX_KHZ=$_l1"
    echo "BIG_MIN_KHZ=$_b0"; echo "BIG_MAX_KHZ=$_b1"
    echo "GPU_MIN_HZ=$_g0"; echo "GPU_MAX_HZ=$_g1"
  } > "$_tmp"
  if validate_candidate_file "$_tmp"; then
    write_hermes_plan "$_tmp" HERMES_LOCAL 86 LAST_PROVEN_GOOD_STRATEGY PROVEN_REUSE
    write_local_vote "$HPLAN" TAKEOVER_LOCAL LAST_PROVEN_GOOD_STRATEGY
    rm -f "$_tmp"
    return 0
  fi
  rm -f "$_tmp"
  return 1
}


opp_next_in_range(){
  _list="$1"; _cur="$2"; _upper="$3"
  printf '%s\n' $_list 2>/dev/null | awk -v c="$_cur" -v u="$_upper" '$1~/^[0-9]+$/&&$1>c&&$1<=u{print $1}' | sort -n | head -n1
}

opp_prev_in_range(){
  _list="$1"; _cur="$2"; _lower="$3"
  printf '%s\n' $_list 2>/dev/null | awk -v c="$_cur" -v l="$_lower" '$1~/^[0-9]+$/&&$1<c&&$1>=l{print $1}' | sort -n | tail -n1
}

power_pressure(){
  _p=$(num "$(kv POWER_MW "$SNAP")")
  _p50=$(num "$(kv POWER_P50_MW "$LEARN")")
  _p95=$(num "$(kv POWER_P95_MW "$LEARN")")
  awk -v p="$_p" -v p50="$_p50" -v p95="$_p95" 'BEGIN{
    if(p<=0||p50<=0) exit 1;
    exit !((p>p50*1.12)||(p95>0&&p>p95))
  }'
}

thermal_pressure(){
  _s=$(num "$(kv SKIN_TEMP_C "$SNAP")")
  _b=$(num "$(kv BATTERY_TEMP_C "$SNAP")")
  _c=$(num "$(kv CPU_TEMP_C "$SNAP")")
  _g=$(num "$(kv GPU_TEMP_C "$SNAP")")
  awk -v s="$_s" -v b="$_b" -v c="$_c" -v g="$_g" 'BEGIN{
    exit !((s>0&&s>=42)||(b>0&&b>=42)||(c>0&&c>=70)||(g>0&&g>=68))
  }'
}

frame_critical(){
  _fps=$(num "$(kv FPS_EST "$SNAP")"); _j=$(num "$(kv JANK_PCT "$SNAP")")
  _p95=$(num "$(kv P95_MS "$SNAP")"); _p99=$(num "$(kv P99_MS "$SNAP")")
  _bfps=$(num "$(kv FPS_P50 "$LEARN")"); _bj=$(num "$(kv JANK_P95 "$LEARN")")
  _bp95=$(num "$(kv FRAME_P95_P95_MS "$LEARN")"); _bp99=$(num "$(kv FRAME_P99_P95_MS "$LEARN")")
  awk -v f="$_fps" -v bf="$_bfps" -v j="$_j" -v bj="$_bj" -v p="$_p95" -v bp="$_bp95" -v q="$_p99" -v bq="$_bp99" 'BEGIN{
    bad=(bf>0&&f>0&&f<bf*0.80)||(bp>0&&p>bp*1.25)||(bq>0&&q>bq*1.25);
    if(bj>0&&j>bj*1.50+2)bad=1;
    exit bad?0:1
  }'
}

local_synthesize_takeover(){
  [ "$(kv STATE "$LEARN")" = READY_HARDWARE_MODEL ] || { HDETAIL=local_synth_model_not_ready; return 1; }
  [ "$(kv FRAME_EVIDENCE "$LEARN")" = VALID ] || { HDETAIL=local_synth_frame_model_not_ready; return 1; }
  [ "$(kv FRAME_EVIDENCE "$SNAP")" = VALID ] || { HDETAIL=local_synth_live_frame_invalid; return 1; }

  _pkg=$(kv ACTIVE_PACKAGE "$SNAP")
  [ "$_pkg" = "$(kv PACKAGE "$WORKLOAD")" ] && [ "$_pkg" = "$(kv PACKAGE "$LEARN")" ] || { HDETAIL=local_synth_context_mismatch; return 1; }

  _skin=$(num "$(kv SKIN_TEMP_C "$SNAP")"); _bat=$(num "$(kv BATTERY_TEMP_C "$SNAP")")
  _cpu=$(num "$(kv CPU_TEMP_C "$SNAP")"); _gpu_t=$(num "$(kv GPU_TEMP_C "$SNAP")")
  # 42C skin is a user-comfort pressure signal, not an absolute planning ban. The hard
  # local safety ceiling remains below 46C skin / 45C battery / 75C CPU+GPU;
  # executor re-checks this continuously and rolls back if crossed.
  awk -v s="$_skin" -v b="$_bat" -v c="$_cpu" -v g="$_gpu_t" 'BEGIN{
    exit !((s<=0||s<46)&&(b<=0||b<45)&&(c<=0||c<75)&&(g<=0||g<75))
  }' || { HDETAIL=local_synth_hard_thermal_guard; return 1; }

  _l0=$(kv LITTLE_MIN_KHZ "$LEARN"); _l1=$(kv LITTLE_MAX_KHZ "$LEARN")
  _b0=$(kv BIG_MIN_KHZ "$LEARN"); _b1=$(kv BIG_MAX_KHZ "$LEARN")
  _g0=$(kv GPU_MIN_HZ "$LEARN"); _g1=$(kv GPU_MAX_HZ "$LEARN")
  _lav=$(kv LITTLE_AVAILABLE_KHZ "$SNAP"); _bav=$(kv BIG_AVAILABLE_KHZ "$SNAP"); _gav=$(kv GPU_AVAILABLE_HZ "$SNAP")
  case "$_l0:$_l1:$_b0:$_b1:$_g0:$_g1" in *[!0-9:]*) HDETAIL=local_synth_invalid_envelope; return 1;; esac

  _nl0="$_l0"; _nl1="$_l1"; _nb0="$_b0"; _nb1="$_b1"; _ng0="$_g0"; _ng1="$_g1"
  _intent=NONE
  _reason=NONE
  _actuators=NONE

  if frame_degraded; then
    _n=$(opp_next_in_range "$_bav" "$_b0" "$_b1"); [ -n "$_n" ] && _nb0="$_n"
    _n=$(opp_next_in_range "$_gav" "$_g0" "$_g1"); [ -n "$_n" ] && _ng0="$_n"
    if frame_critical; then
      _n=$(opp_next_in_range "$_lav" "$_l0" "$_l1"); [ -n "$_n" ] && _nl0="$_n"
      _intent=FRAME_RECOVERY
      _reason=LOCAL_FRAME_CRITICAL_RECOVERY
      _actuators=LITTLE,BIG,GPU
    else
      _intent=FRAME_RECOVERY
      _reason=LOCAL_FRAME_DEGRADED_RECOVERY
      _actuators=BIG,GPU
    fi
  elif power_pressure || thermal_pressure; then
    _n=$(opp_prev_in_range "$_gav" "$_g1" "$_g0")
    if [ -n "$_n" ]; then
      _ng1="$_n"; _intent=POWER_EFFICIENCY; _actuators=GPU
      if thermal_pressure; then _reason=LOCAL_HUMAN_COMFORT_THERMAL_TRIM_GPU; else _reason=LOCAL_POWER_TRIM_GPU; fi
    else
      _n=$(opp_prev_in_range "$_bav" "$_b1" "$_b0")
      if [ -n "$_n" ]; then
        _nb1="$_n"; _intent=POWER_EFFICIENCY; _reason=LOCAL_POWER_TRIM_BIG; _actuators=BIG
      else
        _n=$(opp_prev_in_range "$_lav" "$_l1" "$_l0")
        [ -n "$_n" ] || { HDETAIL=local_synth_no_lower_opp; return 1; }
        _nl1="$_n"; _intent=POWER_EFFICIENCY; _reason=LOCAL_POWER_TRIM_LITTLE; _actuators=LITTLE
      fi
    fi
  else
    _orows=$(num "$(kv OUTCOME_ROWS "$LEARN")")
    _feedback=$(kv OUTCOME_FEEDBACK "$LEARN")
    [ "$_orows" -eq 0 ] 2>/dev/null && [ "$_feedback" != CAUTION ] || { HDETAIL=local_synth_no_action_needed; return 1; }
    _n=$(opp_prev_in_range "$_gav" "$_g1" "$_g0")
    [ -n "$_n" ] || { HDETAIL=local_synth_no_efficiency_probe_opp; return 1; }
    _ng1="$_n"; _intent=POWER_EFFICIENCY; _reason=LOCAL_MATURE_MODEL_EFFICIENCY_PROBE; _actuators=GPU
  fi

  [ "$_nl0" -le "$_nl1" ] && [ "$_nb0" -le "$_nb1" ] && [ "$_ng0" -le "$_ng1" ] || { HDETAIL=local_synth_invalid_range; return 1; }
  [ "$_nl0" != "$_l0" ] || [ "$_nl1" != "$_l1" ] || [ "$_nb0" != "$_b0" ] || [ "$_nb1" != "$_b1" ] || [ "$_ng0" != "$_g0" ] || [ "$_ng1" != "$_g1" ] || { HDETAIL=local_synth_no_change; return 1; }

  _tmp="$ROOT/runtime/.hermes_local_synth_candidate.$$"
  {
    echo "PACKAGE=$_pkg"
    echo "INTENT=$_intent"
    echo "ACTUATORS=$_actuators"
    echo "LITTLE_MIN_KHZ=$_nl0"; echo "LITTLE_MAX_KHZ=$_nl1"
    echo "BIG_MIN_KHZ=$_nb0"; echo "BIG_MAX_KHZ=$_nb1"
    echo "GPU_MIN_HZ=$_ng0"; echo "GPU_MAX_HZ=$_ng1"
  } > "$_tmp"

  if ! validate_candidate_file "$_tmp"; then
    rm -f "$_tmp"
    return 1
  fi

  _conf=$(kv CONFIDENCE "$LEARN"); case "$_conf" in ''|*[!0-9]*) _conf=80;; esac
  [ "$_conf" -lt 80 ] && _conf=80
  [ "$_conf" -gt 90 ] && _conf=90
  write_hermes_plan "$_tmp" HERMES_LOCAL "$_conf" "$_reason" "$_intent"
  write_local_vote "$HPLAN" TAKEOVER_LOCAL_SYNTH "$_reason"
  rm -f "$_tmp"
  HDETAIL="local_synth_${_reason}"
  return 0
}
cloud_takeover(){
  # Restarting/hot-updating ONE HERMES must never itself spend Cloud neurons.
  # During this short boot guard, local continuity remains available.
  _boot_now=$(date +%s)
  if [ $((_boot_now-HERMES_BOOT_AT)) -lt "$CLOUD_BOOT_GUARD_SEC" ] 2>/dev/null; then
    HCLOUD_STATE=COOLDOWN
    HDETAIL=restart_guard_no_cloud
    return 1
  fi

  # Do not spend cloud neurons on a plan that the local executor cannot safely
  # apply at the current thermal state.
  _skin=$(num "$(kv SKIN_TEMP_C "$SNAP")"); _bat=$(num "$(kv BATTERY_TEMP_C "$SNAP")")
  _cpu=$(num "$(kv CPU_TEMP_C "$SNAP")"); _gpu_t=$(num "$(kv GPU_TEMP_C "$SNAP")")
  awk -v s="$_skin" -v b="$_bat" -v c="$_cpu" -v g="$_gpu_t" 'BEGIN{
    exit !((s<=0||s<46)&&(b<=0||b<45)&&(c<=0||c<75)&&(g<=0||g<75))
  }' || { HCLOUD_STATE=OBSERVE; HDETAIL=cloud_takeover_deferred_hard_thermal_guard; return 1; }

  _now=$(date +%s)
  _last=$(kv AT "$LAST"); case "$_last" in ''|*[!0-9]*) _last=0;; esac
  _ncalls=$(num "$(kv SUCCESS_CALLS "$NEURON")")
  _nupdated=$(kv UPDATED_AT "$NEURON"); case "$_nupdated" in ''|*[!0-9]*) _nupdated=0;; esac
  [ "$_ncalls" -gt 0 ] 2>/dev/null && [ "$_nupdated" -gt "$_last" ] 2>/dev/null && _last="$_nupdated"
  [ $((_now-_last)) -ge "$CLOUD_MIN_INTERVAL" ] || { HCLOUD_STATE=COOLDOWN; HDETAIL=neuron_guard_min_interval; return 1; }

  _token=$(config_value HERMES_ACCESS_KEY)
  [ -n "$_token" ] || { HAUTH=NOT_CONFIGURED; HCLOUD_STATE=NO_KEY; HDETAIL=hermes_access_key_not_found; return 1; }
  HAUTH=CONFIGURED_UNVERIFIED
  _endpoint=$(config_value HERMES_ENDPOINT); [ -n "$_endpoint" ] || _endpoint=$(config_value ENDPOINT)
  [ -n "$_endpoint" ] || _endpoint=https://hermes-cloud-djaeger.moclomper.workers.dev
  case "$_endpoint" in
    */v1/chat|*/chat) _url="$_endpoint" ;;
    *) _base=$(printf '%s' "$_endpoint" | sed 's:/*$::'); _url="$_base/v1/chat" ;;
  esac
  command -v curl >/dev/null 2>&1 || { unset _token; HCLOUD_STATE=UNAVAILABLE; HDETAIL=curl_missing; return 1; }

  _pkg=$(kv ACTIVE_PACKAGE "$SNAP")
  _mode=SMART
  _orows=$(num "$(kv OUTCOME_ROWS "$LEARN")"); _rrows=$(num "$(kv ROLLBACK_ROWS "$LEARN")"); _krows=$(num "$(kv KEEP_ROWS "$LEARN")")
  [ "$_orows" -ge 3 ] 2>/dev/null && [ "$_rrows" -gt "$_krows" ] 2>/dev/null && _mode=DEEP
  HROUTE=$_mode
  _msg="You are ONE HERMES Cloud, the strongest cloud cognition of the same Hermes identity that also runs locally. Gemini primary brain is currently unavailable, so ONE HERMES is deputy-in-control. Reason independently from measured Device Truth and return a safe takeover strategy. Human-comfort optimization is strict: FIRST maximize frame stability because unstable frame pacing is uncomfortable for the user; SECOND, among equally stable strategies, prefer lower thermal load and lower skin temperature because the user is heat-sensitive; THIRD, among equally stable and thermally comfortable strategies, minimize power. Never sacrifice meaningful frame stability merely to reduce temperature or save power. Treat skin temperature at or above 42 C as soft HUMAN_COMFORT_PRESSURE, while hard thermal safety remains local. Do not output commands or paths. Package=$_pkg current_fps=$(kv FPS_EST "$SNAP") current_jank=$(kv JANK_PCT "$SNAP") current_p95=$(kv P95_MS "$SNAP") current_p99=$(kv P99_MS "$SNAP") current_power_mw=$(kv POWER_MW "$SNAP") skin_c=$(kv SKIN_TEMP_C "$SNAP") cpu_c=$(kv CPU_TEMP_C "$SNAP") gpu_c=$(kv GPU_TEMP_C "$SNAP"). Learned envelope little=$(kv LITTLE_MIN_KHZ "$LEARN")-$(kv LITTLE_MAX_KHZ "$LEARN") big=$(kv BIG_MIN_KHZ "$LEARN")-$(kv BIG_MAX_KHZ "$LEARN") gpu=$(kv GPU_MIN_HZ "$LEARN")-$(kv GPU_MAX_HZ "$LEARN"). Kernel OPP little=[$(kv LITTLE_AVAILABLE_KHZ "$SNAP")] big=[$(kv BIG_AVAILABLE_KHZ "$SNAP")] gpu=[$(kv GPU_AVAILABLE_HZ "$SNAP")]. Return exactly nine lines: VERDICT=<OBSERVE|CANDIDATE>, CONFIDENCE=<0..100>, LITTLE_MIN_KHZ=<integer>, LITTLE_MAX_KHZ=<integer>, BIG_MIN_KHZ=<integer>, BIG_MAX_KHZ=<integer>, GPU_MIN_HZ=<integer>, GPU_MAX_HZ=<integer>, REASON=<short_token>."
  _sys="You are ONE HERMES Cloud. You are not a third brain; you are cloud cognition of the same ONE HERMES deputy identity. No root/sysfs authority."
  _req="$ROOT/runtime/.hermes_takeover_request.$$"; _resp="$ROOT/runtime/.hermes_takeover_response.$$"
  printf '{"mode":"%s","task":"djaeger_takeover_strategy","message":"%s","prompt":"%s","system":"%s","fallback":false,"max_tokens":256,"temperature":0.1}' "$_mode" "$(json_escape "$_msg")" "$(json_escape "$_msg")" "$(json_escape "$_sys")" > "$_req"
  chmod 600 "$_req"
  _cfg="$ROOT/runtime/.hermes_takeover_curl.$$"
  printf 'header = "Authorization: Bearer %s"\n' "$_token" > "$_cfg"; chmod 600 "$_cfg"
  HTTP=$(curl --http1.1 --connect-timeout 5 -m 18 -sS -o "$_resp" -w '%{http_code}' -K "$_cfg" -H 'Content-Type: application/json' --data-binary "@$_req" "$_url" 2>/dev/null)
  unset _token
  rm -f "$_cfg"
  if [ "$HTTP" = 200 ] && [ -r "$_resp" ] && grep -Eq '"ok"[[:space:]]*:[[:space:]]*true|"text"[[:space:]]*:' "$_resp" 2>/dev/null; then
    command -v neuron_record_success >/dev/null 2>&1 && neuron_record_success "$_mode" "$_req" "$_resp"
    _raw_model=$(grep -o '"model"[[:space:]]*:[[:space:]]*"[^"]*"' "$_resp" 2>/dev/null | head -n1 | sed 's/.*:[[:space:]]*"//;s/"$//')
    [ -n "$_raw_model" ] || _raw_model=NA
    _raw_delta="$(kv LAST_DELTA "$NEURON")"; [ -n "$_raw_delta" ] || _raw_delta=0
    _cltmp="$CLOUD_LAST.tmp.$"
    {
      echo "AT=$(date +%s)"
      echo "HTTP=200"
      echo "ROUTE=$_mode"
      echo "MODEL=$_raw_model"
      echo "VERDICT=PENDING_PARSE"
      echo "CONFIDENCE=0"
      echo "NEURON_DELTA=$_raw_delta"
    } > "$_cltmp"
    chmod 600 "$_cltmp" 2>/dev/null; mv -f "$_cltmp" "$CLOUD_LAST"
  fi
  rm -f "$_req"
  [ "$HTTP" = 200 ] || { HCLOUD_STATE=HTTP_ERROR; HDETAIL="cloud_takeover_http_$HTTP"; rm -f "$_resp"; return 1; }
  { echo "AT=$_now"; echo "DIGEST=TAKEOVER"; } > "$LAST.tmp.$"; chmod 600 "$LAST.tmp.$"; mv -f "$LAST.tmp.$" "$LAST"
  HAUTH=CONFIGURED
  _text=$(tr '\n' ' ' < "$_resp" 2>/dev/null | sed -n 's/.*"text"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | sed 's/\\n/\n/g;s/\\r//g')
  HMODEL=$(grep -o '"model"[[:space:]]*:[[:space:]]*"[^"]*"' "$_resp" 2>/dev/null | head -n1 | sed 's/.*:[[:space:]]*"//;s/"$//')
  [ -n "$HMODEL" ] || HMODEL=NA
  rm -f "$_resp"
  _gv(){ printf '%s\n' "$_text" | sed -n "s/^$1=//p" | head -n1; }
  _verdict=$(_gv VERDICT); _conf=$(_gv CONFIDENCE)
  _ndelta="$(kv LAST_DELTA "$NEURON")"; [ -n "$_ndelta" ] || _ndelta=0
  _cl_at_saved="$(kv AT "$CLOUD_LAST")"; case "$_cl_at_saved" in ''|*[!0-9]*) _cl_at_saved=$(date +%s);; esac
  _cltmp="$CLOUD_LAST.tmp.$$"
  {
    echo "AT=$_cl_at_saved"
    echo "HTTP=$HTTP"
    echo "ROUTE=$_mode"
    echo "MODEL=$HMODEL"
    echo "VERDICT=${_verdict:-UNKNOWN}"
    echo "CONFIDENCE=${_conf:-0}"
    echo "NEURON_DELTA=$_ndelta"
  } > "$_cltmp"
  chmod 600 "$_cltmp" 2>/dev/null; mv -f "$_cltmp" "$CLOUD_LAST"
  [ "$_verdict" = CANDIDATE ] || { HCLOUD_STATE=OBSERVE; HDETAIL=cloud_requests_observe; return 1; }
  case "$_conf" in ''|*[!0-9]*) HCLOUD_STATE=INVALID; HDETAIL=cloud_confidence_invalid; return 1;; esac
  _tmp="$ROOT/runtime/.hermes_cloud_candidate.$$"
  {
    echo "PACKAGE=$_pkg"
    echo "LITTLE_MIN_KHZ=$(_gv LITTLE_MIN_KHZ)"; echo "LITTLE_MAX_KHZ=$(_gv LITTLE_MAX_KHZ)"
    echo "BIG_MIN_KHZ=$(_gv BIG_MIN_KHZ)"; echo "BIG_MAX_KHZ=$(_gv BIG_MAX_KHZ)"
    echo "GPU_MIN_HZ=$(_gv GPU_MIN_HZ)"; echo "GPU_MAX_HZ=$(_gv GPU_MAX_HZ)"
  } > "$_tmp"
  if ! validate_candidate_file "$_tmp"; then rm -f "$_tmp"; HCLOUD_STATE=REJECTED; return 1; fi
  _reason=$(_gv REASON | tr -cd 'A-Za-z0-9_.:-' | cut -c1-96)
  [ -n "$_reason" ] || _reason=HERMES_CLOUD_TAKEOVER
  if frame_degraded; then _cloud_intent=FRAME_RECOVERY
  elif power_pressure; then _cloud_intent=POWER_EFFICIENCY
  else _cloud_intent=FRAME_FIRST_BALANCED
  fi
  write_hermes_plan "$_tmp" HERMES_CLOUD "$_conf" "$_reason" "$_cloud_intent"
  _d=$(digest "$HPLAN")
  _t="$CLOUD_OUT.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_ONE_HERMES_CLOUD_TAKEOVER_V1"
    echo "AT=$(date +%s)"
    echo "PACKAGE=$_pkg"
    echo "VERDICT=TAKEOVER"
    echo "VOTE=PROPOSE_TAKEOVER"
    echo "CONFIDENCE=$_conf"
    echo "CANDIDATE_DIGEST=$_d"
    echo "REASON=$_reason"
    echo "ROUTE=$_mode"
    echo "MODEL=$HMODEL"
    echo "HTTP_CODE=$HTTP"
    echo "APPLY_AUTHORITY=NONE"
  } > "$_t"
  chmod 600 "$_t"; mv -f "$_t" "$CLOUD_OUT"
  write_local_vote "$HPLAN" TAKEOVER_CLOUD LOCAL_ACCEPTS_ONE_HERMES_CLOUD_PLAN
  rm -f "$_tmp"
  HCLOUD_STATE=TAKEOVER_READY
  HDETAIL=one_hermes_cloud_takeover_ready
  HCLOUD_USED=YES
  return 0
}

while true; do
  HLOCAL_STATE=WAITING
  HCLOUD_STATE=STANDBY
  HDETAIL=waiting_for_brain_state
  HTTP=NA
  HROUTE=LOCAL
  HMODEL=NA
  HAUTH=UNKNOWN
  HMODE=DEPUTY_STANDBY
  HACTIVE_SOURCE=NONE
  HCLOUD_USED=NO

  cloud_probe >/dev/null 2>&1 || true

  if [ ! -r "$SNAP" ] || [ ! -r "$LEARN" ]; then
    rm -f "$HPLAN" "$LOCAL_OUT"
    write_state WAITING
    sleep 30
    continue
  fi

  if [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" != GAME ]; then
    rm -f "$HPLAN" "$LOCAL_OUT"
    HLOCAL_STATE=OBSERVE
    HMODE=DEPUTY_STANDBY
    HDETAIL=non_game_workload
    write_state OBSERVING
    sleep 5
    continue
  fi

  if gemini_live; then
    rm -f "$HPLAN"
    HMODE=DEPUTY_SHADOW
    HACTIVE_SOURCE=GEMINI
    HCLOUD_USED=NO
    if [ -r "$GEM" ]; then
      if validate_candidate_file "$GEM"; then
        write_local_vote "$GEM" ACCEPT_PRIMARY GEMINI_PRIMARY_ASSIMILATED_BY_ONE_HERMES
        HLOCAL_STATE=ASSIMILATED_GEMINI
        HDETAIL=gemini_primary_plan_held_by_one_hermes
      else
        rm -f "$LOCAL_OUT"
        HLOCAL_STATE=PRIMARY_REJECTED_LOCAL_CONTEXT
      fi
    else
      rm -f "$LOCAL_OUT"
      HLOCAL_STATE=DEPUTY_STANDBY
      HDETAIL=gemini_online_observe_or_rate_guard
    fi
    write_state GEMINI_PRIMARY
    sleep 30
    continue
  fi

  if ! gemini_failed; then
    rm -f "$HPLAN" "$LOCAL_OUT"
    HMODE=DEPUTY_STANDBY
    HLOCAL_STATE=WAITING
    HDETAIL=gemini_not_ready_not_failed
    write_state WAITING
    sleep 30
    continue
  fi

  HMODE=TAKEOVER
  HACTIVE_SOURCE=HERMES_H2

  # Gemini unavailable: ONE HERMES Cloud is the preferred deputy cognition.
  # Attempt cloud first (neuron-guarded by cloud_takeover itself); local memory
  # remains the immediate fallback when cloud is unavailable, guarded, invalid,
  # or asks to observe.
  if cloud_takeover; then
    HLOCAL_STATE=TAKEOVER_CLOUD
    HACTIVE_SOURCE=HERMES_CLOUD
    HMODE=TAKEOVER_CLOUD_ESCALATED
    write_state HERMES_TAKEOVER
    sleep 45
    continue
  fi

  # Human comfort beats blind reuse when frame is already healthy but the
  # device is physically hot for this user. Try a measured lower-load strategy
  # first; if no safe trim exists, proven history remains the fallback.
  if ! frame_degraded && thermal_pressure; then
    if local_synthesize_takeover; then
      HLOCAL_STATE=TAKEOVER_LOCAL_SYNTH
      HACTIVE_SOURCE=HERMES_LOCAL
      HCLOUD_USED=NO
      write_state HERMES_TAKEOVER
      sleep 10
      continue
    fi
  fi

  if local_history_takeover; then
    HLOCAL_STATE=TAKEOVER_LOCAL
    HACTIVE_SOURCE=HERMES_LOCAL
    HCLOUD_USED=NO
    HDETAIL=local_memory_reuses_proven_strategy
    write_state HERMES_TAKEOVER
    sleep 10
    continue
  fi

  if local_synthesize_takeover; then
    HLOCAL_STATE=TAKEOVER_LOCAL_SYNTH
    HACTIVE_SOURCE=HERMES_LOCAL
    HCLOUD_USED=NO
    write_state HERMES_TAKEOVER
    sleep 10
    continue
  fi

  if ! frame_degraded && ! power_pressure; then
    rm -f "$HPLAN" "$LOCAL_OUT"
    HLOCAL_STATE=TAKEOVER_OBSERVE
    HACTIVE_SOURCE=HERMES_LOCAL
    HDETAIL=gemini_offline_local_model_no_action_needed
    write_state HERMES_TAKEOVER
    sleep 15
    continue
  fi

  if cloud_takeover; then
    HLOCAL_STATE=TAKEOVER_CLOUD
    HACTIVE_SOURCE=HERMES_CLOUD
    HMODE=TAKEOVER_CLOUD_ESCALATED
    write_state HERMES_TAKEOVER
    sleep 45
    continue
  fi

  rm -f "$HPLAN" "$LOCAL_OUT"
  HLOCAL_STATE=TAKEOVER_OBSERVE
  HACTIVE_SOURCE=HERMES_LOCAL
  HDETAIL=no_safe_takeover_strategy
  write_state HERMES_TAKEOVER
  sleep 15
done
