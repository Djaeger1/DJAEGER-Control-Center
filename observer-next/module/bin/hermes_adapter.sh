#!/system/bin/sh

# ONE HERMES adapter for Observer Next.
# HERMES Local is a deterministic, measured-envelope validator. HERMES Cloud
# reviews the exact Gemini candidate. Neither path can write hardware state.

ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
WORKLOAD="$ROOT/runtime/workload.env"
LEARN="$ROOT/history/learned_envelope.env"
GEM="$ROOT/policy/gemini_proposal.env"
LOCAL_OUT="$ROOT/policy/hermes_local_vote.env"
CLOUD_OUT="$ROOT/policy/hermes_cloud_vote.env"
STATE="$ROOT/runtime/hermes_adapter.env"
LAST="$ROOT/config/hermes_review_last.env"

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
  rm -f "$curlcfg" "$req"
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

while true; do
  HLOCAL_STATE=WAITING; HCLOUD_STATE=STANDBY; HDETAIL=waiting_for_candidate; HTTP=NA; HROUTE=LOCAL; HMODEL=NA; HAUTH=UNKNOWN
  cloud_probe >/dev/null 2>&1 || true
  if [ ! -r "$SNAP" ] || [ ! -r "$LEARN" ]; then write_state WAITING; sleep 30; continue; fi
  if [ ! -r "$GEM" ]; then write_state OBSERVING; sleep 30; continue; fi

  if ! local_validate; then
    rm -f "$LOCAL_OUT" "$CLOUD_OUT"
    write_state LOCAL_REJECTED
    sleep 60
    continue
  fi

  cloud_review || true
  write_state REVIEWED
  sleep 60
done
