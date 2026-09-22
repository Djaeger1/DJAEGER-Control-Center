#!/system/bin/sh
# DJAEGER AI live Hermes Cloud neuron accounting.
# Contract:
# - USED_EST / 10000 means DJAEGER Hermes Cloud usage for the current UTC day.
# - UTC day rollover is 00:00 UTC = 07:00 WIB.
# - Only successful Hermes Cloud inference increments usage.
# - Local Hermes, Gemini, telemetry, probes/status checks, and failed requests cost 0.
# - Provider quota errors never force USED_EST to 10000.

ROOT="$1"
STATE="$ROOT/config/hermes_neuron_live.env"
LIMIT=10000

kv(){ sed -n "s/^$1=//p" "$STATE" 2>/dev/null | head -n1; }
num(){ case "$1" in ''|*[!0-9]*) echo 0;; *) echo "$1";; esac; }
utc_day(){ date -u +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d; }

write_state(){
  _day="$1"; _used="$2"; _fast="$3"; _smart="$4"; _deep="$5"; _calls="$6"; _delta="$7"; _method="$8"
  _tmp="$STATE.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_NEURON_LIVE_V1"
    echo "UTC_DAY=$_day"
    echo "RESET_AT=00:00_UTC"
    echo "RESET_AT_WIB=07:00"
    echo "USED_EST=$_used"
    echo "LIMIT=$LIMIT"
    echo "FAST_CALLS=$_fast"
    echo "SMART_CALLS=$_smart"
    echo "DEEP_CALLS=$_deep"
    echo "SUCCESS_CALLS=$_calls"
    echo "LAST_DELTA=$_delta"
    echo "METHOD=$_method"
    echo "ESTIMATED=YES"
    echo "SOURCE=LIVE_SUCCESSFUL_HERMES_CLOUD_ONLY"
    echo "UPDATED_AT=$(date +%s)"
  } > "$_tmp"
  chmod 600 "$_tmp" 2>/dev/null
  mv -f "$_tmp" "$STATE"
}

neuron_reset_if_needed(){
  _today="$(utc_day)"
  _day="$(kv UTC_DAY)"
  if [ "$_day" != "$_today" ]; then
    write_state "$_today" 0 0 0 0 0 0 DAILY_ROLLOVER
  elif [ ! -s "$STATE" ]; then
    write_state "$_today" 0 0 0 0 0 0 INITIALIZED
  fi
}

neuron_record_success(){
  _mode="$1"; _req="$2"; _resp="$3"
  neuron_reset_if_needed

  _used="$(num "$(kv USED_EST)")"
  _fast="$(num "$(kv FAST_CALLS)")"
  _smart="$(num "$(kv SMART_CALLS)")"
  _deep="$(num "$(kv DEEP_CALLS)")"
  _calls="$(num "$(kv SUCCESS_CALLS)")"

  _in_bytes=$(wc -c < "$_req" 2>/dev/null | tr -dc '0-9')
  _out_bytes=$(wc -c < "$_resp" 2>/dev/null | tr -dc '0-9')
  _in_bytes="$(num "$_in_bytes")"; _out_bytes="$(num "$_out_bytes")"
  _tin=$(((_in_bytes+3)/4))
  _tout=$(((_out_bytes+3)/4))

  case "$_mode" in
    FAST)  _rin=5500;  _rout=36400;  _fast=$((_fast+1)) ;;
    DEEP)  _rin=45455; _rout=136364; _deep=$((_deep+1)) ;;
    *)     _mode=SMART; _rin=9091; _rout=27273; _smart=$((_smart+1)) ;;
  esac

  _weighted=$((_tin*_rin + _tout*_rout))
  _delta=$(((_weighted+999999)/1000000))
  [ "$_delta" -lt 1 ] && _delta=1

  _used=$((_used+_delta))
  [ "$_used" -gt "$LIMIT" ] && _used="$LIMIT"
  _calls=$((_calls+1))

  write_state "$(utc_day)" "$_used" "$_fast" "$_smart" "$_deep" "$_calls" "$_delta" "TOKEN_ESTIMATE_${_mode}"
}

neuron_reset_if_needed
