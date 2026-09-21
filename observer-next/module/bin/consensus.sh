#!/system/bin/sh
ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
LEARN="$ROOT/history/learned_envelope.env"
GEM="$ROOT/policy/gemini_proposal.env"
HL="$ROOT/policy/hermes_local_vote.env"
HC="$ROOT/policy/hermes_cloud_vote.env"
OUT="$ROOT/policy/candidate.env"
STATE="$ROOT/runtime/consensus.env"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }

contains_freq(){
  value="$1"
  list="$2"
  case "$value" in ''|*[!0-9]*) return 1;; esac
  [ -n "$list" ] && [ "$list" != "NA" ] || return 1
  for x in $list; do
    case "$x" in ''|*[!0-9]*) continue;; esac
    [ "$x" = "$value" ] && return 0
  done
  return 1
}

while true; do
  GS=ABSENT; LS=ABSENT; CS=OPTIONAL
  [ -r "$GEM" ] && GS=$(kv VERDICT "$GEM")
  [ -r "$HL" ] && LS=$(kv VOTE "$HL")
  [ -r "$HC" ] && CS=$(kv VOTE "$HC")

  CSTATE=OBSERVING
  if [ "$GS" = CANDIDATE ] && [ "$LS" = VALIDATE_BASELINE ]; then
    GC=$(kv CONFIDENCE "$GEM"); LC=$(kv CONFIDENCE "$HL")
    case "$GC:$LC" in
      *[!0-9:]*|:*) CSTATE=INVALID_VOTE;;
      *)
        if [ "$GC" -ge 90 ] && [ "$LC" -ge 70 ]; then
          PKG=$(kv PACKAGE "$GEM")
          if [ "$PKG" != "$(kv PACKAGE "$LEARN")" ]; then
            CSTATE=CONTEXT_MISMATCH
          elif [ "$(kv STATE "$LEARN")" != READY_HARDWARE_MODEL ] || [ "$(kv FRAME_EVIDENCE "$LEARN")" != VALID ]; then
            CSTATE=BASELINE_NOT_MATURE
          else
            LP=$(kv LITTLE_POLICY_PATH "$SNAP")
            BP=$(kv BIG_POLICY_PATH "$SNAP")
            GP=$(kv GPU_DEVFREQ_PATH "$SNAP")
            LAV=$(kv LITTLE_AVAILABLE_KHZ "$SNAP")
            BAV=$(kv BIG_AVAILABLE_KHZ "$SNAP")
            GAV=$(kv GPU_AVAILABLE_HZ "$SNAP")

            GLMIN=$(kv LITTLE_MIN_KHZ "$GEM"); GLMAX=$(kv LITTLE_MAX_KHZ "$GEM")
            GBMIN=$(kv BIG_MIN_KHZ "$GEM"); GBMAX=$(kv BIG_MAX_KHZ "$GEM")
            GGMIN=$(kv GPU_MIN_HZ "$GEM"); GGMAX=$(kv GPU_MAX_HZ "$GEM")

            if [ -z "$LP" ] || [ -z "$BP" ] || [ -z "$GP" ]; then
              CSTATE=HARDWARE_PATH_UNAVAILABLE
            elif ! contains_freq "$GLMIN" "$LAV" || ! contains_freq "$GLMAX" "$LAV" ||                  ! contains_freq "$GBMIN" "$BAV" || ! contains_freq "$GBMAX" "$BAV" ||                  ! contains_freq "$GGMIN" "$GAV" || ! contains_freq "$GGMAX" "$GAV"; then
              CSTATE=UNSUPPORTED_FREQUENCY
              rm -f "$OUT"
            else
              T="$OUT.tmp.$$"
              {
                echo "SCHEMA=DJAEGER_ADAPTIVE_POLICY_V1"
                echo "AT=$(date +%s)"
                echo "PACKAGE=$PKG"
                echo "VERDICT=PROPOSED"
                echo "CONFIDENCE=$GC"
                echo "CONSENSUS=GEMINI_PLUS_HERMES_LOCAL"
                echo "HERMES_CLOUD_VOTE=$CS"
                echo "SHADOW_PASS=NO"
                echo "EXECUTOR_ENABLED=0"
                echo "SYSFS|$LP/scaling_min_freq|$GLMIN"
                echo "SYSFS|$LP/scaling_max_freq|$GLMAX"
                echo "SYSFS|$BP/scaling_min_freq|$GBMIN"
                echo "SYSFS|$BP/scaling_max_freq|$GBMAX"
                echo "SYSFS|$GP/min_freq|$GGMIN"
                echo "SYSFS|$GP/max_freq|$GGMAX"
              } > "$T"
              chmod 600 "$T"; mv -f "$T" "$OUT"
              CSTATE=PENDING_SHADOW
            fi
          fi
        else
          CSTATE=LOW_CONFIDENCE
        fi
      ;;
    esac
  fi

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
