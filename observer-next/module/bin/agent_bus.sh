#!/system/bin/sh
ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
LEARN="$ROOT/history/learned_envelope.env"
BUS="$ROOT/runtime/agent_bus.env"
REQ="$ROOT/runtime/agent_request.txt"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }

while true; do
  [ -r "$SNAP" ] || { sleep 5; continue; }

  {
    echo "DJAEGER_AGENT_OBSERVATION"
    cat "$SNAP"
    echo
    echo "DJAEGER_LEARNED_BASELINE"
    cat "$LEARN" 2>/dev/null
    echo
    echo "OBJECTIVE=understand stock CPU GPU power thermal and frame behavior before proposing adaptive policy"
    echo "OUTPUT_CONTRACT=structured policy only; no raw shell commands; no unrestricted sysfs"
    echo "APPLY_RULE=shadow test plus validator plus rollback required"
  } > "$REQ"

  GSTATE=$(kv GEMINI_STATE "$ROOT/runtime/gemini_reasoner.env")
  HLOCAL=$(kv HERMES_LOCAL_STATE "$ROOT/runtime/hermes_adapter.env")
  HCLOUD=$(kv HERMES_CLOUD_STATE "$ROOT/runtime/hermes_adapter.env")
  CONS=$(kv CONSENSUS_STATE "$ROOT/runtime/consensus.env")
  [ -n "$GSTATE" ] || GSTATE=WAITING
  [ -n "$HLOCAL" ] || HLOCAL=WAITING
  [ -n "$HCLOUD" ] || HCLOUD=STANDBY
  [ -n "$CONS" ] || CONS=OBSERVING

  T="$BUS.tmp.$$"
  {
    echo "AI_BUS=READY"
    echo "HERMES_LOCAL=$HLOCAL"
    echo "HERMES_CLOUD=$HCLOUD"
    echo "GEMINI=$GSTATE"
    echo "CONSENSUS_MODE=REQUIRED"
    echo "CONSENSUS_STATE=$CONS"
    echo "POLICY_INPUT=$REQ"
    echo "POLICY_OUTPUT=$ROOT/policy/candidate.env"
    if [ "$CONS" = PENDING_SHADOW ]; then
      echo "POLICY_STATE=PENDING_SHADOW"
    elif [ -f "$ROOT/policy/candidate.env" ]; then
      echo "POLICY_STATE=CANDIDATE_HELD"
    else
      echo "POLICY_STATE=OBSERVING"
    fi
  } > "$T"
  chmod 644 "$T"
  mv -f "$T" "$BUS"
  sleep 15
done
