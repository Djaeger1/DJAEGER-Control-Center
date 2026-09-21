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
          else
            LP=$(kv LITTLE_POLICY_PATH "$SNAP")
            BP=$(kv BIG_POLICY_PATH "$SNAP")
            GP=$(kv GPU_DEVFREQ_PATH "$SNAP")
            if [ -n "$LP" ] && [ -n "$BP" ] && [ -n "$GP" ]; then
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
                echo "SYSFS|$LP/scaling_min_freq|$(kv LITTLE_MIN_KHZ "$GEM")"
                echo "SYSFS|$LP/scaling_max_freq|$(kv LITTLE_MAX_KHZ "$GEM")"
                echo "SYSFS|$BP/scaling_min_freq|$(kv BIG_MIN_KHZ "$GEM")"
                echo "SYSFS|$BP/scaling_max_freq|$(kv BIG_MAX_KHZ "$GEM")"
                echo "SYSFS|$GP/min_freq|$(kv GPU_MIN_HZ "$GEM")"
                echo "SYSFS|$GP/max_freq|$(kv GPU_MAX_HZ "$GEM")"
              } > "$T"
              chmod 600 "$T"; mv -f "$T" "$OUT"
              CSTATE=PENDING_SHADOW
            else
              CSTATE=HARDWARE_PATH_UNAVAILABLE
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
