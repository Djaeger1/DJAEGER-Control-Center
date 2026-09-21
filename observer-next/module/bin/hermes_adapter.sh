#!/system/bin/sh
ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
LEARN="$ROOT/history/learned_envelope.env"
ENGINE="$ROOT/recovery/engine/module"
OLDSTATE=/data/adb/djaeger_ai
LOCAL_OUT="$ROOT/policy/hermes_local_vote.env"
CLOUD_OUT="$ROOT/policy/hermes_cloud_vote.env"
STATE="$ROOT/runtime/hermes_adapter.env"
LAST_CLOUD="$ROOT/config/hermes_cloud_last_at"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
qget(){ awk -v k="$1" 'index($0,k"=\047")==1 && substr($0,length($0),1)=="\047"{print substr($0,length(k)+3,length($0)-length(k)-3);exit}' "$2" 2>/dev/null; }
write_state(){
  t="$STATE.tmp.$$"
  {
    echo "HERMES_ADAPTER_STATE=$1"
    echo "HERMES_LOCAL_STATE=${HLOCAL_STATE:-UNAVAILABLE}"
    echo "HERMES_CLOUD_STATE=${HCLOUD_STATE:-STANDBY}"
    echo "UPDATED_AT=$(date +%s)"
  } > "$t"; chmod 600 "$t"; mv -f "$t" "$STATE"
}

while true; do
  [ -r "$SNAP" ] && [ -r "$LEARN" ] || { HLOCAL_STATE=WAITING; HCLOUD_STATE=STANDBY; write_state WAITING; sleep 30; continue; }
  [ "$(kv STATE "$LEARN")" = READY_HARDWARE_MODEL ] || { HLOCAL_STATE=WAITING_BASELINE; HCLOUD_STATE=STANDBY; write_state WAITING; sleep 30; continue; }

  HLOCAL="$ENGINE/system/bin/djaeger-hermes-local"
  HCLOUD="$ENGINE/system/bin/djaeger-hermes-cloud"
  PKG=$(kv ACTIVE_PACKAGE "$SNAP"); [ -n "$PKG" ] || PKG=UNKNOWN
  SKIN=$(kv SKIN_TEMP_C "$SNAP"); CPU=$(kv CPU_TEMP_C "$SNAP"); GPUT=$(kv GPU_TEMP_C "$SNAP"); BAT=$(kv BATTERY_TEMP_C "$SNAP")
  LMIN=$(kv LITTLE_MIN_KHZ "$LEARN"); LMAX=$(kv LITTLE_MAX_KHZ "$LEARN")
  BMIN=$(kv BIG_MIN_KHZ "$LEARN"); BMAX=$(kv BIG_MAX_KHZ "$LEARN")
  GMIN=$(kv GPU_MIN_HZ "$LEARN"); GMAX=$(kv GPU_MAX_HZ "$LEARN")
  CONF=$(kv CONFIDENCE "$LEARN"); SAMPLES=$(kv SAMPLES "$LEARN")

  HLOCAL_STATE=UNAVAILABLE
  if [ -r "$HLOCAL" ] && [ -d "$OLDSTATE" ]; then
    chmod 700 "$HLOCAL" 2>/dev/null
    mkdir -p "$OLDSTATE/hermes" 2>/dev/null
    DJAEGER_MODDIR="$ENGINE" DJAEGER_STATE_DIR="$OLDSTATE" sh "$HLOCAL" think STEADY FOREGROUND "$PKG" AUTO       "${SKIN:-0}" "${CPU:-0}" "${GPUT:-0}" "${BAT:-0}" 0 0 0 0 STABLE       READY_HARDWARE_MODEL STABLE "${CONF:-90}" "${SAMPLES:-600}"       "$LMIN" "$LMAX" "$BMIN" "$BMAX" "$GMIN" "$GMAX" >/dev/null 2>&1 || true

    PROP="$OLDSTATE/hermes/proposal.env"
    if [ -r "$PROP" ]; then
      MODE=$(qget CONTROL_MODE "$PROP"); PCONF=$(qget CONFIDENCE "$PROP")
      PLMIN=$(qget LITTLE_MIN "$PROP"); PLMAX=$(qget LITTLE_MAX "$PROP")
      PBMIN=$(qget BIG_MIN "$PROP"); PBMAX=$(qget BIG_MAX "$PROP")
      PGMIN=$(qget GPU_MIN "$PROP"); PGMAX=$(qget GPU_MAX "$PROP")
      PST=$(qget STATE "$PROP")
      if [ "$PST" = VALID ] && [ "$MODE" = DYNAMIC ] &&          [ "$PLMIN:$PLMAX:$PBMIN:$PBMAX:$PGMIN:$PGMAX" = "$LMIN:$LMAX:$BMIN:$BMAX:$GMIN:$GMAX" ]; then
        HLOCAL_STATE=VALIDATED_BASELINE
        {
          echo "SCHEMA=DJAEGER_HERMES_LOCAL_VOTE_V1"
          echo "AT=$(date +%s)"
          echo "PACKAGE=$PKG"
          echo "VOTE=VALIDATE_BASELINE"
          echo "CONFIDENCE=${PCONF:-0}"
          echo "ENVELOPE_MATCH=YES"
          echo "APPLY_AUTHORITY=NONE"
        } > "$LOCAL_OUT.tmp.$$"
        chmod 600 "$LOCAL_OUT.tmp.$$"; mv -f "$LOCAL_OUT.tmp.$$" "$LOCAL_OUT"
      else
        HLOCAL_STATE=ADVISORY_ONLY
      fi
    else
      HLOCAL_STATE=NO_PROPOSAL
    fi
  fi

  HCLOUD_STATE=STANDBY
  GEM="$ROOT/policy/gemini_proposal.env"
  NOW=$(date +%s); LAST=$(cat "$LAST_CLOUD" 2>/dev/null); case "$LAST" in ''|*[!0-9]*) LAST=0;; esac
  if [ -r "$HCLOUD" ] && [ -r "$GEM" ] && [ -d "$OLDSTATE" ] && [ $((NOW-LAST)) -ge 900 ]; then
    chmod 700 "$HCLOUD" 2>/dev/null
    mkdir -p "$OLDSTATE/hermes" 2>/dev/null
    printf '%s\n' "$NOW" > "$LAST_CLOUD"; chmod 600 "$LAST_CLOUD"
    DJAEGER_MODDIR="$ENGINE" DJAEGER_STATE_DIR="$OLDSTATE" sh "$HCLOUD" request-async STEADY FOREGROUND "$PKG" AUTO       "${SKIN:-0}" "${CPU:-0}" "${GPUT:-0}" "${BAT:-0}" 0 0 0 0 STABLE >/dev/null 2>&1 || true
    sleep 2
    CP="$OLDSTATE/hermes/cloud_proposal.env"
    if [ -r "$CP" ] && [ "$(qget STATE "$CP")" = VALID ]; then
      HCLOUD_STATE=ADVISORY_READY
      {
        echo "SCHEMA=DJAEGER_HERMES_CLOUD_VOTE_V1"
        echo "AT=$(date +%s)"
        echo "PACKAGE=$PKG"
        echo "VOTE=ADVISORY_READY"
        echo "CONFIDENCE=$(qget CONFIDENCE "$CP")"
        echo "ROUTE=$(qget ROUTE "$CP")"
        echo "APPLY_AUTHORITY=NONE"
      } > "$CLOUD_OUT.tmp.$$"
      chmod 600 "$CLOUD_OUT.tmp.$$"; mv -f "$CLOUD_OUT.tmp.$$" "$CLOUD_OUT"
    else
      HCLOUD_STATE=NO_VALID_PROPOSAL
    fi
  fi

  write_state READY
  sleep 60
done
