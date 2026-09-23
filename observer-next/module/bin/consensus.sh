#!/system/bin/sh

# Brain arbitration contract:
# GEMINI is PRIMARY/HIGHEST while online and valid.
# ONE HERMES (Local + Cloud, one identity) is the deputy takeover brain.
# AI Agent remains the only device/hardware controller; this file only binds strategy.

ROOT="$1"
BIN_DIR="${0%/*}"
if [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim consensus
fi
SNAP="$ROOT/runtime/snapshot.env"
WORKLOAD="$ROOT/runtime/workload.env"
LEARN="$ROOT/history/learned_envelope.env"
GEM="$ROOT/policy/gemini_proposal.env"
GSTATE="$ROOT/runtime/gemini_reasoner.env"
HP="$ROOT/policy/hermes_proposal.env"
HL="$ROOT/policy/hermes_local_vote.env"
HSTATE="$ROOT/runtime/hermes_adapter.env"
OUT="$ROOT/policy/candidate.env"
STATE="$ROOT/runtime/consensus.env"
SHADOW="$ROOT/runtime/shadow_contextual_v4.env"

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

gemini_live(){
  case "$1" in CANDIDATE|OBSERVE|READY) return 0;; *) return 1;; esac
}

gemini_failed(){
  case "$1" in ALL_KEYS_COOLDOWN|AUTH_ERROR|HTTP_ERROR|NO_KEY|UNAVAILABLE) return 0;; *) return 1;; esac
}

while true; do
  CSTATE=OBSERVING
  BRAIN_SOURCE=NONE
  STRATEGY_FILE=
  STRATEGY_CONF=0
  REQUIRED_CONF=101
  GS=$(kv GEMINI_STATE "$GSTATE"); [ -n "$GS" ] || GS=WAITING
  HV=$(kv VOTE "$HL"); [ -n "$HV" ] || HV=ABSENT
  HM=$(kv HERMES_MODE "$HSTATE"); [ -n "$HM" ] || HM=DEPUTY_STANDBY
  HA=$(kv HERMES_ACTIVE_SOURCE "$HSTATE"); [ -n "$HA" ] || HA=HERMES_H2

  if gemini_live "$GS"; then
    BRAIN_SOURCE=GEMINI
    if [ -r "$GEM" ] && [ "$(kv VERDICT "$GEM")" = CANDIDATE ]; then
      gd=$(digest "$GEM")
      hd=$(kv CANDIDATE_DIGEST "$HL")
      if [ "$HV" = ACCEPT_PRIMARY ] && [ -n "$gd" ] && [ "$gd" = "$hd" ]; then
        STRATEGY_FILE="$GEM"
        STRATEGY_CONF=$(kv CONFIDENCE "$GEM")
        REQUIRED_CONF=85
        CSTATE=GEMINI_PRIMARY_READY
      else
        CSTATE=WAITING_ONE_HERMES_ASSIMILATION
      fi
    else
      CSTATE=GEMINI_PRIMARY_OBSERVE
    fi
  elif gemini_failed "$GS"; then
    BRAIN_SOURCE=HERMES_H2
    if [ -r "$HP" ] && [ "$(kv VERDICT "$HP")" = CANDIDATE ]; then
      hd=$(digest "$HP")
      ld=$(kv CANDIDATE_DIGEST "$HL")
      if [ -n "$hd" ] && [ "$hd" = "$ld" ]; then
        STRATEGY_FILE="$HP"
        _actual=$(kv BRAIN_SOURCE "$HP")
        case "$_actual" in
          HERMES_LOCAL) BRAIN_SOURCE=HERMES_LOCAL; REQUIRED_CONF=80 ;;
          HERMES_CLOUD) BRAIN_SOURCE=HERMES_CLOUD; REQUIRED_CONF=75 ;;
          *) BRAIN_SOURCE=HERMES_H2; REQUIRED_CONF=85 ;;
        esac
        STRATEGY_CONF=$(kv CONFIDENCE "$HP")
        CSTATE=HERMES_DEPUTY_READY
      else
        CSTATE=HERMES_TAKEOVER_DIGEST_MISMATCH
      fi
    else
      case "$HA" in
        HERMES_LOCAL) BRAIN_SOURCE=HERMES_LOCAL ;;
        HERMES_CLOUD) BRAIN_SOURCE=HERMES_CLOUD ;;
        *) BRAIN_SOURCE=HERMES_H2 ;;
      esac
      CSTATE=HERMES_DEPUTY_OBSERVE
    fi
  else
    CSTATE=WAITING_PRIMARY_STATE
  fi

  if [ -n "$STRATEGY_FILE" ]; then
    case "$STRATEGY_CONF" in ''|*[!0-9]*) CSTATE=INVALID_CONFIDENCE; STRATEGY_FILE=;; esac
  fi

  if [ -n "$STRATEGY_FILE" ] && [ "$STRATEGY_CONF" -lt "$REQUIRED_CONF" ] 2>/dev/null; then
    CSTATE=LOW_CONFIDENCE
    STRATEGY_FILE=
  fi

  if [ -n "$STRATEGY_FILE" ]; then
    PKG=$(kv PACKAGE "$STRATEGY_FILE")
    AT=$(kv AT "$STRATEGY_FILE"); case "$AT" in ''|*[!0-9]*) AT=0;; esac
    AGE=$(( $(date +%s) - AT ))
    if [ "$AGE" -lt 0 ] || [ "$AGE" -gt 900 ]; then
      CSTATE=STALE_STRATEGY
      STRATEGY_FILE=
    elif [ "$(kv WORKLOAD_CLASS "$WORKLOAD")" != GAME ]; then
      CSTATE=NON_GAME_BLOCKED
      STRATEGY_FILE=
    elif [ "$(kv PACKAGE "$WORKLOAD")" != "$PKG" ] || [ "$(kv ACTIVE_PACKAGE "$SNAP")" != "$PKG" ]; then
      CSTATE=ACTIVE_WORKLOAD_MISMATCH
      STRATEGY_FILE=
    elif [ "$(kv PACKAGE "$LEARN")" != "$PKG" ]; then
      CSTATE=CONTEXT_MISMATCH
      STRATEGY_FILE=
    elif [ "$(kv STATE "$LEARN")" != READY_HARDWARE_MODEL ] || [ "$(kv FRAME_EVIDENCE "$LEARN")" != VALID ]; then
      CSTATE=BASELINE_NOT_MATURE
      STRATEGY_FILE=
    fi
  fi

  if [ -n "$STRATEGY_FILE" ]; then
    INTENT=$(kv INTENT "$STRATEGY_FILE"); [ -n "$INTENT" ] || INTENT=FRAME_FIRST_BALANCED
    ACTUATORS=$(kv ACTUATORS "$STRATEGY_FILE"); [ -n "$ACTUATORS" ] || ACTUATORS=ALL
    case "$ACTUATORS" in
      ALL|LITTLE|BIG|GPU|LITTLE,BIG|LITTLE,GPU|BIG,GPU|LITTLE,BIG,GPU) ;;
      *) CSTATE=INVALID_ACTUATOR_MASK; STRATEGY_FILE= ;;
    esac
    LP=$(kv LITTLE_POLICY_PATH "$SNAP"); BP=$(kv BIG_POLICY_PATH "$SNAP"); GP=$(kv GPU_DEVFREQ_PATH "$SNAP")
    LAV=$(kv LITTLE_AVAILABLE_KHZ "$SNAP"); BAV=$(kv BIG_AVAILABLE_KHZ "$SNAP"); GAV=$(kv GPU_AVAILABLE_HZ "$SNAP")
    LMIN=$(kv LITTLE_MIN_KHZ "$STRATEGY_FILE"); LMAX=$(kv LITTLE_MAX_KHZ "$STRATEGY_FILE")
    BMIN=$(kv BIG_MIN_KHZ "$STRATEGY_FILE"); BMAX=$(kv BIG_MAX_KHZ "$STRATEGY_FILE")
    GMIN=$(kv GPU_MIN_HZ "$STRATEGY_FILE"); GMAX=$(kv GPU_MAX_HZ "$STRATEGY_FILE")
    if [ -z "$LP" ] || [ -z "$BP" ] || [ -z "$GP" ]; then
      CSTATE=HARDWARE_PATH_UNAVAILABLE
      STRATEGY_FILE=
    elif ! contains_freq "$LMIN" "$LAV" || ! contains_freq "$LMAX" "$LAV" || \
         ! contains_freq "$BMIN" "$BAV" || ! contains_freq "$BMAX" "$BAV" || \
         ! contains_freq "$GMIN" "$GAV" || ! contains_freq "$GMAX" "$GAV"; then
      CSTATE=UNSUPPORTED_FREQUENCY
      STRATEGY_FILE=
    fi
  fi

  if [ -n "$STRATEGY_FILE" ]; then
    sd=$(digest "$STRATEGY_FILE")
    _t="$OUT.tmp.$$"
    {
      echo "SCHEMA=DJAEGER_ADAPTIVE_POLICY_V3"
      echo "AT=$(kv AT "$STRATEGY_FILE")"
      echo "PACKAGE=$(kv PACKAGE "$STRATEGY_FILE")"
      echo "VERDICT=PROPOSED"
      echo "CONFIDENCE=$STRATEGY_CONF"
      echo "INTENT=$INTENT"
      echo "ACTUATORS=$ACTUATORS"
      echo "BRAIN_SOURCE=$BRAIN_SOURCE"
      echo "PRIMARY_BRAIN=GEMINI"
      echo "DEPUTY_BRAIN=HERMES_H2"
      echo "ONE_HERMES=LOCAL_PLUS_CLOUD_ONE_IDENTITY"
      echo "OBJECTIVE=HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD"
      echo "CONSENSUS=PRIMARY_OR_DEPUTY_BOUND_TO_LOCAL_DEVICE_TRUTH"
      echo "CANDIDATE_DIGEST=$sd"
      echo "SHADOW_PASS=NO"
      echo "EXECUTOR_ENABLED=0"
      echo "LITTLE_MIN_KHZ=$LMIN"
      echo "LITTLE_MAX_KHZ=$LMAX"
      echo "BIG_MIN_KHZ=$BMIN"
      echo "BIG_MAX_KHZ=$BMAX"
      echo "GPU_MIN_HZ=$GMIN"
      echo "GPU_MAX_HZ=$GMAX"
    } > "$_t"
    chmod 600 "$_t"; mv -f "$_t" "$OUT"

    # A matching shadow result is authoritative for this exact digest.
    # Do not keep reporting PENDING after the evaluator has already decided.
    _shadow_digest="$(kv CANDIDATE_DIGEST "$SHADOW")"
    _shadow_state="$(kv SHADOW_STATE "$SHADOW")"
    if [ "$_shadow_digest" = "$sd" ]; then
      case "$_shadow_state" in
        PASS) CSTATE=SHADOW_PASS ;;
        REJECT) CSTATE=SHADOW_REJECTED ;;
        *) CSTATE=PENDING_SHADOW ;;
      esac
    else
      CSTATE=PENDING_SHADOW
    fi
  else
    rm -f "$OUT"
  fi

  _t="$STATE.tmp.$$"
  {
    echo "CONSENSUS_STATE=$CSTATE"
    echo "ACTIVE_BRAIN_SOURCE=$BRAIN_SOURCE"
    echo "GEMINI_STATE=$GS"
    echo "HERMES_MODE=$HM"
    echo "HERMES_LOCAL_VOTE=$HV"
    echo "SHADOW_STATE=$(kv SHADOW_STATE "$SHADOW")"
    echo "SHADOW_REASON=$(kv SHADOW_REASON "$SHADOW")"
    echo "SHADOW_DIGEST=$(kv CANDIDATE_DIGEST "$SHADOW")"
    echo "OBJECTIVE=HUMAN_COMFORT_FRAME_FIRST_THERMAL_SECOND_MINIMUM_POWER_THIRD"
    echo "UPDATED_AT=$(date +%s)"
  } > "$_t"
  chmod 600 "$_t"; mv -f "$_t" "$STATE"
  # Local arbitration is cheap and should react quickly to a fresh brain proposal.
  sleep 5
done
