#!/system/bin/sh

ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
WORKLOAD="$ROOT/runtime/workload.env"
LEARN="$ROOT/history/learned_envelope.env"
GEM="$ROOT/policy/gemini_proposal.env"
HL="$ROOT/policy/hermes_local_vote.env"
HC="$ROOT/policy/hermes_cloud_vote.env"
OUT="$ROOT/policy/candidate.env"
STATE="$ROOT/runtime/consensus.env"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }

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

while true; do
  GS=ABSENT; LS=ABSENT; CS=ABSENT
  [ -r "$GEM" ] && GS=$(kv VERDICT "$GEM")
  [ -r "$HL" ] && LS=$(kv VOTE "$HL")
  [ -r "$HC" ] && CS=$(kv VOTE "$HC")
  CSTATE=OBSERVING

  if [ "$GS" = CANDIDATE ]; then
    CSTATE=WAITING_HERMES_REVIEW
    gd=$(digest "$GEM")
    ld=$(kv CANDIDATE_DIGEST "$HL")
    cd=$(kv CANDIDATE_DIGEST "$HC")
    if [ "$LS" = VALIDATE_CANDIDATE ] && [ "$CS" = APPROVE_CANDIDATE ]; then
      if [ -z "$gd" ] || [ "$gd" != "$ld" ] || [ "$gd" != "$cd" ]; then
        CSTATE=REVIEW_DIGEST_MISMATCH
      else
        GC=$(kv CONFIDENCE "$GEM"); LC=$(kv CONFIDENCE "$HL"); CC=$(kv CONFIDENCE "$HC")
        case "$GC:$LC:$CC" in
          *[!0-9:]*|:*) CSTATE=INVALID_VOTE;;
          *)
            if [ "$GC" -lt 85 ] || [ "$LC" -lt 80 ] || [ "$CC" -lt 70 ]; then
              CSTATE=LOW_CONFIDENCE
            elif [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" != GAME ]; then
              CSTATE=NON_GAME_BLOCKED
            elif [ "$(kv PACKAGE "$WORKLOAD")" != "$(kv PACKAGE "$GEM")" ]; then
              CSTATE=ACTIVE_WORKLOAD_MISMATCH
            elif [ "$(kv PACKAGE "$GEM")" != "$(kv PACKAGE "$LEARN")" ]; then
              CSTATE=CONTEXT_MISMATCH
            elif [ "$(kv STATE "$LEARN")" != READY_HARDWARE_MODEL ] || [ "$(kv FRAME_EVIDENCE "$LEARN")" != VALID ]; then
              CSTATE=BASELINE_NOT_MATURE
            else
              LP=$(kv LITTLE_POLICY_PATH "$SNAP"); BP=$(kv BIG_POLICY_PATH "$SNAP"); GP=$(kv GPU_DEVFREQ_PATH "$SNAP")
              LAV=$(kv LITTLE_AVAILABLE_KHZ "$SNAP"); BAV=$(kv BIG_AVAILABLE_KHZ "$SNAP"); GAV=$(kv GPU_AVAILABLE_HZ "$SNAP")
              GLMIN=$(kv LITTLE_MIN_KHZ "$GEM"); GLMAX=$(kv LITTLE_MAX_KHZ "$GEM")
              GBMIN=$(kv BIG_MIN_KHZ "$GEM"); GBMAX=$(kv BIG_MAX_KHZ "$GEM")
              GGMIN=$(kv GPU_MIN_HZ "$GEM"); GGMAX=$(kv GPU_MAX_HZ "$GEM")
              if [ -z "$LP" ] || [ -z "$BP" ] || [ -z "$GP" ]; then
                CSTATE=HARDWARE_PATH_UNAVAILABLE
              elif ! contains_freq "$GLMIN" "$LAV" || ! contains_freq "$GLMAX" "$LAV" || \
                   ! contains_freq "$GBMIN" "$BAV" || ! contains_freq "$GBMAX" "$BAV" || \
                   ! contains_freq "$GGMIN" "$GAV" || ! contains_freq "$GGMAX" "$GAV"; then
                CSTATE=UNSUPPORTED_FREQUENCY
              else
                T="$OUT.tmp.$$"
                {
                  echo "SCHEMA=DJAEGER_ADAPTIVE_POLICY_V2"
                  echo "AT=$(kv AT "$GEM")"
                  echo "PACKAGE=$(kv PACKAGE "$GEM")"
                  echo "VERDICT=PROPOSED"
                  echo "CONFIDENCE=$GC"
                  echo "CONSENSUS=GEMINI_PLUS_HERMES_LOCAL_PLUS_HERMES_CLOUD"
                  echo "CANDIDATE_DIGEST=$gd"
                  echo "SHADOW_PASS=NO"
                  echo "EXECUTOR_ENABLED=0"
                  echo "LITTLE_MIN_KHZ=$GLMIN"
                  echo "LITTLE_MAX_KHZ=$GLMAX"
                  echo "BIG_MIN_KHZ=$GBMIN"
                  echo "BIG_MAX_KHZ=$GBMAX"
                  echo "GPU_MIN_HZ=$GGMIN"
                  echo "GPU_MAX_HZ=$GGMAX"
                } > "$T"
                chmod 600 "$T"; mv -f "$T" "$OUT"
                CSTATE=PENDING_SHADOW
              fi
            fi
          ;;
        esac
      fi
    fi
  fi

  [ "$CSTATE" = PENDING_SHADOW ] || rm -f "$OUT"
  T="$STATE.tmp.$$"
  {
    echo "CONSENSUS_STATE=$CSTATE"
    echo "GEMINI_VOTE=$GS"
    echo "HERMES_LOCAL_VOTE=$LS"
    echo "HERMES_CLOUD_VOTE=$CS"
    echo "UPDATED_AT=$(date +%s)"
  } > "$T"
  chmod 600 "$T"; mv -f "$T" "$STATE"
  sleep 30
done
