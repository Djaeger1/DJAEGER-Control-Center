#!/system/bin/sh
ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
BUS="$ROOT/runtime/agent_bus.env"
REQ="$ROOT/runtime/agent_request.txt"

present() {
  grep -Rils "$1" "$ROOT/recovery/legacy" 2>/dev/null | head -n1 | grep -q .
}

while true; do
  [ -r "$SNAP" ] || { sleep 5; continue; }

  GEMINI=NOT_FOUND
  HERMES=NOT_FOUND
  present 'GEMINI' && GEMINI=RESTORED
  present 'HERMES\|DJAEGER_ACCESS_TOKEN\|CLOUD' && HERMES=RESTORED

  {
    echo "DJAEGER_AGENT_OBSERVATION"
    cat "$SNAP"
    echo "OBJECTIVE=learn stock CPU/GPU/power/thermal/frame behavior and propose measurable improvements"
    echo "OUTPUT_CONTRACT=structured policy only; no raw shell commands; no unrestricted sysfs"
  } > "$REQ"

  TMP="$BUS.tmp.$$"
  {
    echo "AI_BUS=READY"
    echo "HERMES_LOCAL=ADAPTER_READY"
    echo "HERMES_CLOUD=$HERMES"
    echo "GEMINI=$GEMINI"
    echo "CONSENSUS_MODE=REQUIRED"
    echo "POLICY_INPUT=$REQ"
    echo "POLICY_OUTPUT=$ROOT/policy/candidate.env"
    if [ -f "$ROOT/policy/candidate.env" ]; then
      echo "POLICY_STATE=CANDIDATE_READY"
    else
      echo "POLICY_STATE=OBSERVING"
    fi
  } > "$TMP"
  chmod 644 "$TMP"
  mv -f "$TMP" "$BUS"
  sleep 15
done
