#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
S="$M/bin/shadow.sh"
W="$R/runtime/reject_quarantine_patch"
mkdir -p "$W" || exit 1

HT1="$W/hermes.1"
HT2="$W/hermes.2"
ST1="$W/shadow.1"
ST2="$W/shadow.2"
HS="$W/hermes_semantic.snip"
CS="$W/cloud_guard.snip"
SS="$W/shadow_persist.snip"

cat > "$HS" <<'EOF'
  # PERSISTENT_SHADOW_REJECT_QUARANTINE
  _rj="$ROOT/history/shadow_reject_strategy.env"
  if [ -r "$_rj" ]; then
    _rjat="$(kv AT "$_rj")"
    case "$_rjat" in ''|*[!0-9]*) _rjat=0;; esac
    _rjage=$(( $(date +%s) - _rjat ))
    [ "$_rjage" -ge 0 ] 2>/dev/null || _rjage=999999
    if [ "$_rjage" -le 900 ] 2>/dev/null &&
       [ "$(kv PACKAGE "$_rj")" = "$_pkg" ] &&
       [ "$(kv INTENT "$_rj")" = "$_intent" ] &&
       [ "$(kv ACTUATORS "$_rj")" = "$_actuators" ] &&
       [ "$(kv LITTLE_MIN_KHZ "$_rj")" = "$_nl0" ] &&
       [ "$(kv LITTLE_MAX_KHZ "$_rj")" = "$_nl1" ] &&
       [ "$(kv BIG_MIN_KHZ "$_rj")" = "$_nb0" ] &&
       [ "$(kv BIG_MAX_KHZ "$_rj")" = "$_nb1" ] &&
       [ "$(kv GPU_MIN_HZ "$_rj")" = "$_ng0" ] &&
       [ "$(kv GPU_MAX_HZ "$_rj")" = "$_ng1" ]; then
      rm -f "$_tmp" "$HPLAN" "$LOCAL_OUT"
      HDETAIL=shadow_rejected_strategy_quarantine
      return 1
    fi
  fi
EOF

cat > "$CS" <<'EOF'
  # REJECT_QUARANTINE_NO_CLOUD
  if [ "$HDETAIL" = shadow_rejected_strategy_quarantine ]; then
    HCLOUD_STATE=REACHABLE_IDLE
    return 1
  fi
EOF

cat > "$SS" <<'EOF'
  # PERSIST_REJECT_STRATEGY
  if [ "$_state" = REJECT ] && [ -r "$POLICY" ]; then
    _rt="$REJECT_LEDGER.tmp.$$"
    {
      echo "AT=$_now"
      echo "PACKAGE=$(kv PACKAGE "$POLICY")"
      echo "INTENT=$(kv INTENT "$POLICY")"
      echo "ACTUATORS=$(kv ACTUATORS "$POLICY")"
      echo "LITTLE_MIN_KHZ=$(kv LITTLE_MIN_KHZ "$POLICY")"
      echo "LITTLE_MAX_KHZ=$(kv LITTLE_MAX_KHZ "$POLICY")"
      echo "BIG_MIN_KHZ=$(kv BIG_MIN_KHZ "$POLICY")"
      echo "BIG_MAX_KHZ=$(kv BIG_MAX_KHZ "$POLICY")"
      echo "GPU_MIN_HZ=$(kv GPU_MIN_HZ "$POLICY")"
      echo "GPU_MAX_HZ=$(kv GPU_MAX_HZ "$POLICY")"
      echo "REASON=$_reason"
    } > "$_rt"
    chmod 600 "$_rt"
    mv -f "$_rt" "$REJECT_LEDGER"
  fi
EOF

if grep -Fq "PERSISTENT_SHADOW_REJECT_QUARANTINE" "$H"; then
  cp "$H" "$HT1"
else
  awk -v SNIP="$HS" '
    BEGIN{inside=0; done=0}
    {
      print
      if ($0 == "  _tmp=\"$ROOT/runtime/.hermes_local_synth_candidate.$$\"") {
        inside=1
        next
      }
      if (inside && $0 == "  } > \"$_tmp\"" && !done) {
        while ((getline x < SNIP) > 0) print x
        close(SNIP)
        done=1
        inside=0
      }
    }
    END{if(!done) exit 42}
  ' "$H" > "$HT1" || exit 42
fi

if grep -Fq "REJECT_QUARANTINE_NO_CLOUD" "$HT1"; then
  cp "$HT1" "$HT2"
else
  awk -v SNIP="$CS" '
    BEGIN{done=0}
    {
      print
      if ($0 == "cloud_takeover(){" && !done) {
        while ((getline x < SNIP) > 0) print x
        close(SNIP)
        done=1
      }
    }
    END{if(!done) exit 43}
  ' "$HT1" > "$HT2" || exit 43
fi

if grep -Fq 'REJECT_LEDGER="$ROOT/history/shadow_reject_strategy.env"' "$S"; then
  cp "$S" "$ST1"
else
  awk '
    BEGIN{done=0}
    {
      print
      if ($0 == "APPROVAL=\"$ROOT/policy/approved.env\"" && !done) {
        print "REJECT_LEDGER=\"$ROOT/history/shadow_reject_strategy.env\""
        done=1
      }
    }
    END{if(!done) exit 44}
  ' "$S" > "$ST1" || exit 44
fi

if grep -Fq "PERSIST_REJECT_STRATEGY" "$ST1"; then
  cp "$ST1" "$ST2"
else
  awk -v SNIP="$SS" '
    BEGIN{done=0}
    {
      print
      if ($0 == "  chmod 600 \"$t\"; mv -f \"$t\" \"$OUT\"" && !done) {
        while ((getline x < SNIP) > 0) print x
        close(SNIP)
        done=1
      }
    }
    END{if(!done) exit 45}
  ' "$ST1" > "$ST2" || exit 45
fi

sh -n "$HT2" || exit 51
sh -n "$ST2" || exit 52

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_persistent_reject.$TS" || exit 61
cp "$S" "$R/runtime/shadow.pre_persistent_reject.$TS" || exit 62

cp "$HT2" "$H" || exit 63
cp "$ST2" "$S" || exit 64
chmod 755 "$H" "$S"

RJ="$R/history/shadow_reject_strategy.env"
{
  echo "AT=$(date +%s)"
  echo "PACKAGE=sts.al"
  echo "INTENT=POWER_EFFICIENCY"
  echo "ACTUATORS=GPU"
  echo "LITTLE_MIN_KHZ=940800"
  echo "LITTLE_MAX_KHZ=1708800"
  echo "BIG_MIN_KHZ=1401600"
  echo "BIG_MAX_KHZ=2054400"
  echo "GPU_MIN_HZ=390000000"
  echo "GPU_MAX_HZ=770000000"
  echo "REASON=human_comfort_contract_failed_POWER_EFFICIENCY"
} > "$RJ"
chmod 600 "$RJ"

for N in hermes_adapter shadow; do
  P=$(cat "$R/runtime/locks/$N.lock/pid" 2>/dev/null)
  case "$P" in
    ""|*[!0-9]*) ;;
    *)
      kill -TERM "$P" 2>/dev/null
      sleep 1
      kill -0 "$P" 2>/dev/null && kill -KILL "$P" 2>/dev/null
      ;;
  esac
  rm -rf "$R/runtime/locks/$N.lock"
done

nohup sh "$H" "$R" "$M" >/dev/null 2>&1 &
nohup sh "$S" "$R" "$M" >/dev/null 2>&1 &

echo "PATCH=PERSISTENT_REJECT_QUARANTINE_ACTIVE"
echo "HERMES_SYNTAX=OK"
echo "SHADOW_SYNTAX=OK"
