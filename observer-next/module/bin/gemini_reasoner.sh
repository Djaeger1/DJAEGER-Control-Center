#!/system/bin/sh
ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
LEARN="$ROOT/history/learned_envelope.env"
OUT="$ROOT/policy/gemini_proposal.env"
STATE="$ROOT/runtime/gemini_reasoner.env"
LEGACY="$ROOT/recovery/legacy"
SLOTFILE="$ROOT/config/gemini_slot"
LASTFILE="$ROOT/config/gemini_last_at"
COOLDOWN=1800

kv() { sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
safe_num(){ case "$1" in ''|*[!0-9.-]*) echo 0;; *) echo "$1";; esac; }

write_state(){
  t="$STATE.tmp.$$"
  {
    echo "GEMINI_STATE=$1"
    echo "GEMINI_DETAIL=$2"
    echo "GEMINI_KEY_COUNT=${KEY_COUNT:-0}"
    echo "GEMINI_SLOT=${SLOT:-0}"
    echo "GEMINI_HTTP=${HTTP:-NA}"
    echo "UPDATED_AT=$(date +%s)"
  } > "$t"
  chmod 600 "$t"; mv -f "$t" "$STATE"
}

collect_keys(){
  KF="$ROOT/runtime/.gemini_keys.$$"
  : > "$KF"
  find "$LEGACY" -maxdepth 5 -type f 2>/dev/null | while read -r f; do
    sed -n       -e "s/^[[:space:]]*\(GEMINI_API_KEY\|API_KEY\|KEY_[1-4]\|KEY\)[[:space:]]*=[[:space:]]*['\"]\{0,1\}\([^'\"[:space:]]\{20,\}\).*/\2/p"       -e 's/.*\(AIza[0-9A-Za-z_-]\{20,\}\).*/\1/p' "$f" 2>/dev/null
  done | awk 'NF && !seen[$0]++' | head -n 4 > "$KF"
  KEY_COUNT=$(wc -l < "$KF" 2>/dev/null)
}

while true; do
  [ -r "$SNAP" ] && [ -r "$LEARN" ] || { write_state WAITING "observer_or_learning_missing"; sleep 30; continue; }
  LSTATE=$(kv STATE "$LEARN")
  [ "$LSTATE" = READY_HARDWARE_MODEL ] || { write_state WAITING "baseline_not_mature"; sleep 30; continue; }

  FRAME=$(kv FRAME_EVIDENCE "$LEARN")
  NOW=$(date +%s); LAST=$(cat "$LASTFILE" 2>/dev/null)
  case "$LAST" in ''|*[!0-9]*) LAST=0;; esac
  [ $((NOW-LAST)) -ge "$COOLDOWN" ] || { write_state COOLDOWN "quota_guard"; sleep 60; continue; }

  command -v curl >/dev/null 2>&1 || { write_state UNAVAILABLE "curl_missing"; sleep 120; continue; }
  collect_keys
  [ "${KEY_COUNT:-0}" -gt 0 ] || { write_state NO_KEY "restored_gemini_key_not_found"; rm -f "$KF"; sleep 120; continue; }

  MODEL=""
  for f in "$LEGACY/gemini.conf" "$LEGACY/config/gemini.conf" "$LEGACY/configs/gemini.conf"; do
    [ -r "$f" ] || continue
    MODEL=$(sed -n "s/^[[:space:]]*MODEL[[:space:]]*=[[:space:]]*['\"]\{0,1\}\([A-Za-z0-9._-]*\).*/\1/p" "$f" | head -n1)
    [ -n "$MODEL" ] && break
  done
  [ -n "$MODEL" ] || MODEL="gemini-3.8-flash"

  SLOT=$(cat "$SLOTFILE" 2>/dev/null); case "$SLOT" in ''|*[!0-9]*) SLOT=1;; esac
  [ "$SLOT" -ge 1 ] && [ "$SLOT" -le "$KEY_COUNT" ] || SLOT=1
  KEY=$(sed -n "${SLOT}p" "$KF")
  NEXT=$((SLOT+1)); [ "$NEXT" -gt "$KEY_COUNT" ] && NEXT=1
  echo "$NEXT" > "$SLOTFILE"; chmod 600 "$SLOTFILE"
  rm -f "$KF"

  PKG=$(kv ACTIVE_PACKAGE "$SNAP" | tr -cd 'A-Za-z0-9._-')
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

  PAY="$ROOT/runtime/.gemini_request.$"
  RESP="$ROOT/runtime/.gemini_response.$$"
  cat > "$PAY" <<EOF
{"contents":[{"parts":[{"text":"You are one reasoning member of DJAEGER Observer. Analyze only measured stock behavior. Package=$PKG samples=$SAMPLES independent_frame_windows=$FRAME_WINDOWS. Stock envelope: little=$LMIN-$LMAX kHz big=$BMIN-$BMAX kHz gpu=$GMIN-$GMAX Hz. Kernel supported little frequencies=[$LAV], big frequencies=[$BAV], gpu frequencies=[$GAV]. Stock frame baseline: fps_p50=$FPS50 jank_p95=$JANK95 frame_p95_p95_ms=$FP95 frame_p99_p95_ms=$FP99. Current: little=$LCUR big=$BCUR gpu=$GCUR skin=$SKIN C cpu=$CPU C gpuTemp=$GPUC C power=$POWER mW fps=$CFPS jank=$CJANK p95=$CP95 p99=$CP99. Goal: frame stability first, then lower power and temperature. Never output shell commands or paths. Choose OBSERVE when evidence does not justify a change. A CANDIDATE must stay inside learned stock envelope and every selected frequency must be an exact member of its kernel-supported list. Return exactly nine lines: VERDICT=OBSERVE_or_CANDIDATE, CONFIDENCE=0_to_100, LITTLE_MIN_KHZ=integer, LITTLE_MAX_KHZ=integer, BIG_MIN_KHZ=integer, BIG_MAX_KHZ=integer, GPU_MIN_HZ=integer, GPU_MAX_HZ=integer, REASON=short_token."}]}],"generationConfig":{"temperature":0.1,"maxOutputTokens":256}}
EOF

  HTTP=$(curl -sS --connect-timeout 5 --max-time 15 -o "$RESP" -w '%{http_code}'     -H 'Content-Type: application/json'     -H "x-goog-api-key: $KEY"     -X POST "https://generativelanguage.googleapis.com/v1beta/models/$MODEL:generateContent"     --data-binary "@$PAY" 2>/dev/null)
  rm -f "$PAY"
  echo "$NOW" > "$LASTFILE"; chmod 600 "$LASTFILE"

  [ "$HTTP" = 200 ] || { write_state HTTP_ERROR "request_failed"; rm -f "$RESP"; sleep 120; continue; }

  TEXT=$(tr '\n' ' ' < "$RESP" 2>/dev/null | sed -n 's/.*"text"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | sed 's/\\n/\n/g;s/\\r//g')
  rm -f "$RESP"
  gv(){ printf '%s\n' "$TEXT" | sed -n "s/^$1=//p" | head -n1; }

  VERDICT=$(gv VERDICT); CONF=$(gv CONFIDENCE)
  GLMIN=$(gv LITTLE_MIN_KHZ); GLMAX=$(gv LITTLE_MAX_KHZ)
  GBMIN=$(gv BIG_MIN_KHZ); GBMAX=$(gv BIG_MAX_KHZ)
  GGMIN=$(gv GPU_MIN_HZ); GGMAX=$(gv GPU_MAX_HZ)
  REASON=$(gv REASON | tr -cd 'A-Za-z0-9_.:-' | cut -c1-96)

  case "$VERDICT" in OBSERVE|OBSERVE_or_CANDIDATE) write_state OBSERVE "ai_requests_more_evidence"; continue;; CANDIDATE) :;; *) write_state INVALID "unparseable_verdict"; continue;; esac
  case "$CONF:$GLMIN:$GLMAX:$GBMIN:$GBMAX:$GGMIN:$GGMAX" in *[!0-9:]*|:*) write_state INVALID "non_numeric_candidate"; continue;; esac

  [ "$GLMIN" -ge "$LMIN" ] && [ "$GLMAX" -le "$LMAX" ] && [ "$GLMIN" -le "$GLMAX" ] || { write_state REJECTED "little_outside_stock"; continue; }
  [ "$GBMIN" -ge "$BMIN" ] && [ "$GBMAX" -le "$BMAX" ] && [ "$GBMIN" -le "$GBMAX" ] || { write_state REJECTED "big_outside_stock"; continue; }
  [ "$GGMIN" -ge "$GMIN" ] && [ "$GGMAX" -le "$GMAX" ] && [ "$GGMIN" -le "$GGMAX" ] || { write_state REJECTED "gpu_outside_stock"; continue; }

  T="$OUT.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_GEMINI_OBSERVER_PROPOSAL_V1"
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
    echo "REASON=${REASON:-GEMINI_OBSERVER_ANALYSIS}"
    echo "FRAME_EVIDENCE=$FRAME"
    echo "APPLY_AUTHORITY=NONE"
  } > "$T"
  chmod 600 "$T"; mv -f "$T" "$OUT"
  write_state CANDIDATE "proposal_created_no_apply_authority"
  sleep 60
done
