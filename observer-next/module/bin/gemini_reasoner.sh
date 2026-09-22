#!/system/bin/sh
# DJAEGER AI Gemini reasoner.
# Four-slot vault with independent cooldowns. HTTP 429 rotates immediately to
# the next READY key; no cloud response has direct hardware authority.

ROOT="$1"
BIN_DIR="${0%/*}"
if [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim gemini_reasoner
fi
SNAP="$ROOT/runtime/snapshot.env"
LEARN="$ROOT/history/learned_envelope.env"
WORKLOAD="$ROOT/runtime/workload.env"
OUT="$ROOT/policy/gemini_proposal.env"
STATE="$ROOT/runtime/gemini_reasoner.env"
VAULT="$ROOT/config/gemini_vault.env"
SLOTFILE="$ROOT/config/gemini_slot"
COOLDOWN_FILE="$ROOT/config/gemini_cooldown.env"
LAST_SUCCESS="$ROOT/config/gemini_last_success"
# Adaptive reasoning cadence. Stable gameplay is intentionally quieter, while
# degraded frame-time, thermal pressure, or high power usage wake Gemini much
# sooner. Hardware is still changed only through consensus -> shadow -> executor.
STABLE_GUARD_SEC=90
FRAME_DEGRADED_GUARD_SEC=45
URGENT_GUARD_SEC=20
POWER_GUARD_SEC=60
RATE_LIMIT_COOLDOWN=1800
AUTH_COOLDOWN=21600
GUARD_SEC=$STABLE_GUARD_SEC
GUARD_REASON=STABLE
LAST_SUCCESS_AGE=999999

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
safe_num(){ case "$1" in ''|*[!0-9.-]*) echo 0;; *) echo "$1";; esac; }
contains_freq(){ _v="$1"; shift; for _x in "$@"; do [ "$_x" = "$_v" ] && return 0; done; return 1; }

key_count(){
  sed -n 's/^KEY_[1-4]=//p' "$VAULT" 2>/dev/null | awk 'NF{n++}END{print n+0}'
}

cooldown_until(){
  _u=$(kv "KEY_$1_UNTIL" "$COOLDOWN_FILE")
  case "$_u" in ''|*[!0-9]*) echo 0;; *) echo "$_u";; esac
}

set_cooldown(){
  _slot="$1"; _until="$2"; _tmp="$COOLDOWN_FILE.tmp.$$"
  { grep -v "^KEY_${_slot}_UNTIL=" "$COOLDOWN_FILE" 2>/dev/null || true; echo "KEY_${_slot}_UNTIL=$_until"; } > "$_tmp"
  chmod 600 "$_tmp"; mv -f "$_tmp" "$COOLDOWN_FILE"
}

key_stats(){
  KEY_COUNT=$(key_count); case "$KEY_COUNT" in ''|*[!0-9]*) KEY_COUNT=0;; esac
  NOW_STATS=$(date +%s); READY_COUNT=0; COOLDOWN_COUNT=0
  _i=1
  while [ "$_i" -le "$KEY_COUNT" ]; do
    _u=$(cooldown_until "$_i")
    if [ "$_u" -gt "$NOW_STATS" ] 2>/dev/null; then COOLDOWN_COUNT=$((COOLDOWN_COUNT+1)); else READY_COUNT=$((READY_COUNT+1)); fi
    _i=$((_i+1))
  done
}

write_state(){
  key_stats
  _t="$STATE.tmp.$$"
  {
    echo "GEMINI_STATE=$1"
    echo "GEMINI_DETAIL=$2"
    echo "GEMINI_KEY_COUNT=$KEY_COUNT"
    echo "GEMINI_READY_COUNT=$READY_COUNT"
    echo "GEMINI_COOLDOWN_COUNT=$COOLDOWN_COUNT"
    echo "GEMINI_ACTIVE_SLOT=${SLOT:-0}"
    echo "GEMINI_HTTP=${HTTP:-NA}"
    echo "GEMINI_GUARD_SEC=${GUARD_SEC:-$STABLE_GUARD_SEC}"
    echo "GEMINI_GUARD_REASON=${GUARD_REASON:-STABLE}"
    echo "GEMINI_LAST_SUCCESS_AGE_SEC=${LAST_SUCCESS_AGE:-999999}"
    echo "UPDATED_AT=$(date +%s)"
  } > "$_t"
  chmod 600 "$_t"; mv -f "$_t" "$STATE"
}

next_ready_slot(){
  key_stats
  [ "$KEY_COUNT" -gt 0 ] || return 1
  _start="$1"; case "$_start" in ''|*[!0-9]*) _start=1;; esac
  [ "$_start" -ge 1 ] && [ "$_start" -le "$KEY_COUNT" ] || _start=1
  _step=0
  while [ "$_step" -lt "$KEY_COUNT" ]; do
    _slot=$(( ((_start-1+_step)%KEY_COUNT)+1 ))
    _u=$(cooldown_until "$_slot")
    if [ "$_u" -le "$(date +%s)" ] 2>/dev/null; then echo "$_slot"; return 0; fi
    _step=$((_step+1))
  done
  return 1
}

adaptive_guard(){
  GUARD_SEC=$STABLE_GUARD_SEC
  GUARD_REASON=STABLE

  _fe=$(kv FRAME_EVIDENCE "$SNAP")
  _fn=$(safe_num "$(kv FRAME_N "$SNAP")")
  _fps=$(safe_num "$(kv FPS_EST "$SNAP")")
  _jank=$(safe_num "$(kv JANK_PCT "$SNAP")")
  _p95=$(safe_num "$(kv P95_MS "$SNAP")")
  _p99=$(safe_num "$(kv P99_MS "$SNAP")")
  _bfps=$(safe_num "$(kv FPS_P50 "$LEARN")")
  _bjank=$(safe_num "$(kv JANK_P95 "$LEARN")")
  _bp95=$(safe_num "$(kv FRAME_P95_P95_MS "$LEARN")")
  _bp99=$(safe_num "$(kv FRAME_P99_P95_MS "$LEARN")")
  _power=$(safe_num "$(kv POWER_MW "$SNAP")")
  _p50w=$(safe_num "$(kv POWER_P50_MW "$LEARN")")
  _skin=$(safe_num "$(kv SKIN_TEMP_C "$SNAP")")
  _cpu=$(safe_num "$(kv CPU_TEMP_C "$SNAP")")
  _gput=$(safe_num "$(kv GPU_TEMP_C "$SNAP")")

  if [ "$_fe" = VALID ] && [ "$_fn" -ge 20 ] 2>/dev/null; then
    if awk -v f="$_fps" -v bf="$_bfps" -v j="$_jank" -v bj="$_bjank" -v p95="$_p95" -v bp95="$_bp95" -v p99="$_p99" -v bp99="$_bp99" 'BEGIN{
      bad=(bf>0&&f>0&&f<bf*0.80)||(bp95>0&&p95>bp95*1.25)||(bp99>0&&p99>bp99*1.25);
      if(bj>0&&j>bj*1.50+2)bad=1;
      exit bad?0:1
    }'; then
      GUARD_SEC=$URGENT_GUARD_SEC
      GUARD_REASON=FRAME_CRITICAL
      return
    fi

    if awk -v f="$_fps" -v bf="$_bfps" -v j="$_jank" -v bj="$_bjank" -v p95="$_p95" -v bp95="$_bp95" -v p99="$_p99" -v bp99="$_bp99" 'BEGIN{
      bad=(bf>0&&f>0&&f<bf*0.95)||(bp95>0&&p95>bp95*1.08)||(bp99>0&&p99>bp99*1.10);
      if(bj>0&&j>bj*1.20+1)bad=1;
      exit bad?0:1
    }'; then
      GUARD_SEC=$FRAME_DEGRADED_GUARD_SEC
      GUARD_REASON=FRAME_DEGRADED
      return
    fi
  fi

  if awk -v s="$_skin" -v c="$_cpu" -v g="$_gput" 'BEGIN{exit !((s>0&&s>=44)||(c>0&&c>=70)||(g>0&&g>=68))}'; then
    GUARD_SEC=30
    GUARD_REASON=THERMAL_PRESSURE
    return
  fi

  if awk -v p="$_power" -v b="$_p50w" 'BEGIN{exit !(p>0&&b>0&&p>b*1.15)}'; then
    GUARD_SEC=$POWER_GUARD_SEC
    GUARD_REASON=POWER_HIGH
    return
  fi
}

while true; do
  [ -r "$SNAP" ] && [ -r "$LEARN" ] || { rm -f "$OUT"; SLOT=0; HTTP=NA; write_state WAITING observer_or_learning_missing; sleep 30; continue; }
  [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" = GAME ] || { rm -f "$OUT"; SLOT=0; HTTP=NA; write_state OBSERVE non_game_workload; sleep 45; continue; }
  [ "$(kv STATE "$LEARN")" = READY_HARDWARE_MODEL ] || { rm -f "$OUT"; SLOT=0; HTTP=NA; write_state WAITING baseline_not_mature; sleep 30; continue; }

  NOW=$(date +%s)
  LAST=$(cat "$LAST_SUCCESS" 2>/dev/null); case "$LAST" in ''|*[!0-9]*) LAST=0;; esac
  LAST_SUCCESS_AGE=$((NOW-LAST)); [ "$LAST_SUCCESS_AGE" -ge 0 ] 2>/dev/null || LAST_SUCCESS_AGE=999999
  adaptive_guard
  if [ "$LAST_SUCCESS_AGE" -lt "$GUARD_SEC" ]; then
    SLOT=0
    HTTP=NA
    write_state READY "adaptive_guard_${GUARD_REASON}_${GUARD_SEC}s"
    sleep 10
    continue
  fi

  command -v curl >/dev/null 2>&1 || { SLOT=0; HTTP=NA; write_state UNAVAILABLE curl_missing; sleep 120; continue; }
  key_stats
  [ "$KEY_COUNT" -gt 0 ] || { rm -f "$OUT"; SLOT=0; HTTP=NA; write_state NO_KEY gemini_key_not_found; sleep 120; continue; }

  MODEL=$(kv GEMINI_MODEL "$ROOT/config/gemini.env"); [ -n "$MODEL" ] || MODEL=gemini-3.6-flash
  START=$(cat "$SLOTFILE" 2>/dev/null); case "$START" in ''|*[!0-9]*) START=1;; esac
  SLOT=$(next_ready_slot "$START") || { HTTP=429; rm -f "$OUT"; write_state ALL_KEYS_COOLDOWN no_ready_key; sleep 60; continue; }

  PKG=$(kv ACTIVE_PACKAGE "$SNAP" | tr -cd 'A-Za-z0-9._-')
  FRAME=$(kv FRAME_EVIDENCE "$LEARN")
  SKIN=$(safe_num "$(kv SKIN_TEMP_C "$SNAP")")
  CPU=$(safe_num "$(kv CPU_TEMP_C "$SNAP")")
  GPUC=$(safe_num "$(kv GPU_TEMP_C "$SNAP")")
  POWER=$(safe_num "$(kv POWER_MW "$SNAP")")
  LCUR=$(safe_num "$(kv LITTLE_CUR_KHZ "$SNAP")")
  BCUR=$(safe_num "$(kv BIG_CUR_KHZ "$SNAP")")
  GCUR=$(safe_num "$(kv GPU_CUR_HZ "$SNAP")")
  LMIN=$(safe_num "$(kv LITTLE_MIN_KHZ "$LEARN")"); LMAX=$(safe_num "$(kv LITTLE_MAX_KHZ "$LEARN")")
  BMIN=$(safe_num "$(kv BIG_MIN_KHZ "$LEARN")"); BMAX=$(safe_num "$(kv BIG_MAX_KHZ "$LEARN")")
  GMIN=$(safe_num "$(kv GPU_MIN_HZ "$LEARN")"); GMAX=$(safe_num "$(kv GPU_MAX_HZ "$LEARN")")
  SAMPLES=$(safe_num "$(kv SAMPLES "$LEARN")")
  FRAME_WINDOWS=$(safe_num "$(kv FRAME_WINDOWS "$LEARN")")
  FPS50=$(safe_num "$(kv FPS_P50 "$LEARN")")
  JANK95=$(safe_num "$(kv JANK_P95 "$LEARN")")
  FP95=$(safe_num "$(kv FRAME_P95_P95_MS "$LEARN")")
  FP99=$(safe_num "$(kv FRAME_P99_P95_MS "$LEARN")")
  CFPS=$(safe_num "$(kv FPS_EST "$SNAP")")
  CJANK=$(safe_num "$(kv JANK_PCT "$SNAP")")
  CP95=$(safe_num "$(kv P95_MS "$SNAP")")
  CP99=$(safe_num "$(kv P99_MS "$SNAP")")
  LAV=$(kv LITTLE_AVAILABLE_KHZ "$SNAP" | tr -cd '0-9 ')
  BAV=$(kv BIG_AVAILABLE_KHZ "$SNAP" | tr -cd '0-9 ')
  GAV=$(kv GPU_AVAILABLE_HZ "$SNAP" | tr -cd '0-9 ')

  PAY="$ROOT/runtime/.gemini_request.$$"
  RESP="$ROOT/runtime/.gemini_response.$$"
  cat > "$PAY" <<EOF
{"contents":[{"parts":[{"text":"You are GEMINI, the PRIMARY and HIGHEST reasoning brain of DJAEGER AI while you are online and valid. Analyze only measured device behavior for the active GAME workload. Package=$PKG samples=$SAMPLES independent_frame_windows=$FRAME_WINDOWS. Measured stock envelope: little=$LMIN-$LMAX kHz big=$BMIN-$BMAX kHz gpu=$GMIN-$GMAX Hz. Kernel supported little frequencies=[$LAV], big frequencies=[$BAV], gpu frequencies=[$GAV]. Frame baseline: fps_p50=$FPS50 jank_p95=$JANK95 frame_p95_p95_ms=$FP95 frame_p99_p95_ms=$FP99. Current: little=$LCUR big=$BCUR gpu=$GCUR skin=$SKIN C cpu=$CPU C gpuTemp=$GPUC C power=$POWER mW fps=$CFPS jank=$CJANK p95=$CP95 p99=$CP99. Optimization contract is lexicographic: FIRST make frame-time as stable as evidence allows; SECOND, among strategies with equivalent frame stability, minimize power. Never trade meaningful frame stability for lower power. Temperature is a local safety constraint, not a reason to sacrifice frame stability inside safe limits. Never output shell commands, paths, legacy profile labels, or unsupported clocks. Choose OBSERVE when evidence does not justify change. A CANDIDATE must remain inside the measured envelope and use exact kernel-supported frequencies. Return exactly nine lines: VERDICT=<OBSERVE|CANDIDATE>, CONFIDENCE=<0..100>, LITTLE_MIN_KHZ=<integer>, LITTLE_MAX_KHZ=<integer>, BIG_MIN_KHZ=<integer>, BIG_MAX_KHZ=<integer>, GPU_MIN_HZ=<integer>, GPU_MAX_HZ=<integer>, REASON=<short_token>."}]}],"generationConfig":{"temperature":0.1,"maxOutputTokens":256}}
EOF
  chmod 600 "$PAY"

  ATTEMPTS=0
  GOT_200=0
  while [ "$ATTEMPTS" -lt "$KEY_COUNT" ]; do
    NOW=$(date +%s)
    _until=$(cooldown_until "$SLOT")
    if [ "$_until" -gt "$NOW" ] 2>/dev/null; then
      SLOT=$(next_ready_slot $((SLOT+1))) || break
      ATTEMPTS=$((ATTEMPTS+1))
      continue
    fi
    KEY=$(sed -n "s/^KEY_${SLOT}=//p" "$VAULT" 2>/dev/null | head -n1)
    if [ -z "$KEY" ]; then
      SLOT=$(next_ready_slot $((SLOT+1))) || break
      ATTEMPTS=$((ATTEMPTS+1))
      continue
    fi
    CURLCFG="$ROOT/runtime/.gemini_curl.$$"
    printf 'header = "x-goog-api-key: %s"\n' "$KEY" > "$CURLCFG"
    chmod 600 "$CURLCFG"
    HTTP=$(curl -sS --connect-timeout 5 --max-time 15 -o "$RESP" -w '%{http_code}' -K "$CURLCFG" -H 'Content-Type: application/json' -X POST "https://generativelanguage.googleapis.com/v1beta/models/$MODEL:generateContent" --data-binary "@$PAY" 2>/dev/null)
    rm -f "$CURLCFG"; unset KEY

    case "$HTTP" in
      200)
        GOT_200=1
        NEXT=$((SLOT+1)); [ "$NEXT" -gt "$KEY_COUNT" ] && NEXT=1
        echo "$NEXT" > "$SLOTFILE"; chmod 600 "$SLOTFILE"
        break
        ;;
      429)
        set_cooldown "$SLOT" $((NOW+RATE_LIMIT_COOLDOWN))
        NEXT=$((SLOT+1)); [ "$NEXT" -gt "$KEY_COUNT" ] && NEXT=1
        echo "$NEXT" > "$SLOTFILE"; chmod 600 "$SLOTFILE"
        SLOT=$(next_ready_slot "$NEXT") || break
        ;;
      401|403)
        set_cooldown "$SLOT" $((NOW+AUTH_COOLDOWN))
        NEXT=$((SLOT+1)); [ "$NEXT" -gt "$KEY_COUNT" ] && NEXT=1
        echo "$NEXT" > "$SLOTFILE"; chmod 600 "$SLOTFILE"
        SLOT=$(next_ready_slot "$NEXT") || break
        ;;
      *)
        break
        ;;
    esac
    ATTEMPTS=$((ATTEMPTS+1))
  done
  rm -f "$PAY"

  if [ "$GOT_200" != 1 ]; then
    rm -f "$OUT" "$RESP"
    case "$HTTP" in
      429) write_state ALL_KEYS_COOLDOWN rate_limited_all_ready_keys ;;
      401|403) write_state AUTH_ERROR key_auth_failed ;;
      000|'') HTTP=000; write_state HTTP_ERROR network_or_timeout ;;
      *) write_state HTTP_ERROR "request_failed_http_${HTTP}" ;;
    esac
    sleep 60
    continue
  fi

  TEXT=$(tr '\n' ' ' < "$RESP" 2>/dev/null | sed -n 's/.*"text"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | sed 's/\\n/\n/g;s/\\r//g')
  rm -f "$RESP"
  gv(){ printf '%s\n' "$TEXT" | tr -d '\\140' | sed -n "s/^[[:space:]>#*-]*$1[[:space:]]*=[[:space:]]*//p" | head -n1; }
  trim(){ printf '%s' "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'; }
  rawv(){ trim "$(gv "$1")"; }
  numv(){
    _raw="$(rawv "$1")"
    # Accept only a single numeric value with optional grouping, decimal .0,
    # quotes/backticks, and the expected harmless unit suffix. Do not extract
    # arbitrary digits from prose/ranges.
    _norm="$(printf '%s' "$_raw" | sed       -e 's/^[`"[:space:]]*//'       -e 's/[`"[:space:]]*$//'       -e 's/[[:space:]]*[kKmMgG]*[hH][zZ][[:space:]]*$//'       -e 's/[[:space:]]*%[[:space:]]*$//'       -e 's/,//g'       -e 's/[[:space:]]//g'       -e 's/\.0*$//')"
    case "$_norm" in ''|*[!0-9]*) return 1;; esac
    printf '%s' "$_norm"
  }
  parse_diag(){
    _d="$ROOT/runtime/gemini_parse_error.env.tmp.$PPID"
    {
      echo "AT=$(date +%s)"
      echo "VERDICT_RAW=$(rawv VERDICT | tr '\r\n' '  ' | cut -c1-80)"
      for _k in CONFIDENCE LITTLE_MIN_KHZ LITTLE_MAX_KHZ BIG_MIN_KHZ BIG_MAX_KHZ GPU_MIN_HZ GPU_MAX_HZ; do
        _rv="$(rawv "$_k" | tr '\r\n' '  ' | cut -c1-80)"
        echo "${_k}_RAW=$_rv"
      done
      echo "REASON_RAW=$(rawv REASON | tr '\r\n' '  ' | cut -c1-96)"
      echo "SECRET_VALUES=NOT_RECORDED"
    } > "$_d"
    chmod 600 "$_d"; mv -f "$_d" "$ROOT/runtime/gemini_parse_error.env"
  }

  VERDICT=$(trim "$(gv VERDICT)" | tr -d '`"')
  CONF=$(numv CONFIDENCE) || CONF=""
  GLMIN=$(numv LITTLE_MIN_KHZ) || GLMIN=""
  GLMAX=$(numv LITTLE_MAX_KHZ) || GLMAX=""
  GBMIN=$(numv BIG_MIN_KHZ) || GBMIN=""
  GBMAX=$(numv BIG_MAX_KHZ) || GBMAX=""
  GGMIN=$(numv GPU_MIN_HZ) || GGMIN=""
  GGMAX=$(numv GPU_MAX_HZ) || GGMAX=""
  REASON=$(trim "$(gv REASON)" | tr -cd 'A-Za-z0-9_.:-' | cut -c1-96)
  echo "$(date +%s)" > "$LAST_SUCCESS"; chmod 600 "$LAST_SUCCESS"

  case "$VERDICT" in
    OBSERVE) rm -f "$OUT"; write_state OBSERVE ai_requests_more_evidence; sleep 15; continue ;;
    CANDIDATE) : ;;
    *) rm -f "$OUT"; write_state INVALID unparseable_verdict; sleep 60; continue ;;
  esac
  case "$CONF:$GLMIN:$GLMAX:$GBMIN:$GBMAX:$GGMIN:$GGMAX" in *[!0-9:]*|:*) parse_diag; rm -f "$OUT"; write_state INVALID non_numeric_candidate; sleep 60; continue;; esac
  [ "$CONF" -ge 0 ] && [ "$CONF" -le 100 ] || { rm -f "$OUT"; write_state INVALID confidence_out_of_range; sleep 60; continue; }
  [ "$GLMIN" -ge "$LMIN" ] && [ "$GLMAX" -le "$LMAX" ] && [ "$GLMIN" -le "$GLMAX" ] || { rm -f "$OUT"; write_state REJECTED little_outside_stock; sleep 60; continue; }
  [ "$GBMIN" -ge "$BMIN" ] && [ "$GBMAX" -le "$BMAX" ] && [ "$GBMIN" -le "$GBMAX" ] || { rm -f "$OUT"; write_state REJECTED big_outside_stock; sleep 60; continue; }
  [ "$GGMIN" -ge "$GMIN" ] && [ "$GGMAX" -le "$GMAX" ] && [ "$GGMIN" -le "$GGMAX" ] || { rm -f "$OUT"; write_state REJECTED gpu_outside_stock; sleep 60; continue; }
  contains_freq "$GLMIN" $LAV && contains_freq "$GLMAX" $LAV || { rm -f "$OUT"; write_state REJECTED unsupported_little_opp; sleep 60; continue; }
  contains_freq "$GBMIN" $BAV && contains_freq "$GBMAX" $BAV || { rm -f "$OUT"; write_state REJECTED unsupported_big_opp; sleep 60; continue; }
  contains_freq "$GGMIN" $GAV && contains_freq "$GGMAX" $GAV || { rm -f "$OUT"; write_state REJECTED unsupported_gpu_opp; sleep 60; continue; }

  T="$OUT.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_GEMINI_PRIMARY_STRATEGY_V3"
    echo "AT=$(date +%s)"
    echo "PACKAGE=$PKG"
    echo "VERDICT=CANDIDATE"
    echo "CONFIDENCE=$CONF"
    echo "LITTLE_MIN_KHZ=$GLMIN"
    echo "LITTLE_MAX_KHZ=$GLMAX"
    echo "BIG_MIN_KHZ=$GBMIN"
    echo "BIG_MAX_KHZ=$GBMAX"
    echo "GPU_MIN_HZ=$GGMIN"
    echo "GPU_MAX_HZ=$GGMAX"
    echo "REASON=${REASON:-GEMINI_PRIMARY_FRAME_FIRST_ANALYSIS}"
    echo "BRAIN_SOURCE=GEMINI"
    echo "BRAIN_ROLE=PRIMARY_HIGHEST"
    echo "OBJECTIVE=FRAME_STABILITY_FIRST_MINIMUM_POWER_SECOND"
    echo "FRAME_EVIDENCE=$FRAME"
    echo "KEY_SLOT=$SLOT"
    echo "APPLY_AUTHORITY=NONE"
  } > "$T"
  chmod 600 "$T"; mv -f "$T" "$OUT"
  write_state CANDIDATE proposal_created_no_apply_authority
  sleep 15
done
