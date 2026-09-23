#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
S="$M/bin/shadow.sh"
MF="$R/history/shadow_reject_strategies.csv"
W="$R/runtime/reject_ledger_multiactuator_fix"
HN="$W/hermes.new"
SN="$W/shadow.new"
MC="$W/reject.cleaned.csv"
BAD="$R/history/shadow_reject_strategies.bad.csv"
mkdir -p "$W" || exit 1

# Hermes matcher: normalize candidate ACTUATORS before CSV comparison.
if grep -Fq "MULTIACTUATOR_MATCHER_NORMALIZE" "$H"; then
  cp "$H" "$HN"
else
  awk '
    {
      print
      if ($0 == "  _qa=$(kv ACTUATORS \"$_qs\")" && !done) {
        print "  # MULTIACTUATOR_MATCHER_NORMALIZE"
        print "  _qa=$(printf \"%s\" \"$_qa\" | tr \047,\047 \047+\047)"
        done=1
      }
    }
    END{if(!done) exit 41}
  ' "$H" > "$HN" || exit 41
fi

# Shadow persistence: normalize ACTUATORS in the multi-reject CSV.
if grep -Fq "MULTIACTUATOR_PERSIST_NORMALIZE" "$S"; then
  cp "$S" "$SN"
else
  awk '
    {
      print
      if ($0 == "      _ma=$(kv ACTUATORS \"$POLICY\")" && !done) {
        print "      # MULTIACTUATOR_PERSIST_NORMALIZE"
        print "      _ma=$(printf \"%s\" \"$_ma\" | tr \047,\047 \047+\047)"
        done=1
      }
    }
    END{if(!done) exit 42}
  ' "$S" > "$SN" || exit 42
fi

sh -n "$HN" || exit 51
sh -n "$SN" || exit 52

grep -Fq "MULTIACTUATOR_MATCHER_NORMALIZE" "$HN" || exit 53
grep -Fq "MULTIACTUATOR_PERSIST_NORMALIZE" "$SN" || exit 54
grep -Fq "MULTI_REJECT_ALTERNATIVE_SYNTH" "$HN" || exit 55
grep -Fq "PERSIST_REJECT_STRATEGY_MULTI" "$SN" || exit 56

# Repair only the known comma-split BIG,GPU rows. Keep unknown malformed rows
# out of the active ledger and preserve them separately for forensics.
if [ -r "$MF" ]; then
  : > "$BAD"
  awk -F, -v OFS=, -v bad="$BAD" '
    NR==1 {print; next}
    NF==11 {print; next}
    NF==12 && $4=="BIG" && $5=="GPU" {
      print $1,$2,$3,"BIG+GPU",$6,$7,$8,$9,$10,$11,$12
      next
    }
    {print > bad}
  ' "$MF" > "$MC" || exit 55

  awk -F, 'NR==1{next} NF!=11{bad=1} END{exit bad?1:0}' "$MC" || exit 56
else
  echo "AT,PACKAGE,INTENT,ACTUATORS,LITTLE_MIN_KHZ,LITTLE_MAX_KHZ,BIG_MIN_KHZ,BIG_MAX_KHZ,GPU_MIN_HZ,GPU_MAX_HZ,REASON" > "$MC"
fi

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_multiactuator_fix.$TS" || exit 61
cp "$S" "$R/runtime/shadow.pre_multiactuator_fix.$TS" || exit 62
[ ! -r "$MF" ] || cp "$MF" "$R/runtime/shadow_reject_strategies.pre_multiactuator_fix.$TS.csv" || exit 63

cp "$HN" "$H" || exit 64
cp "$SN" "$S" || exit 65
cp "$MC" "$MF" || exit 66
chmod 755 "$H" "$S"
chmod 600 "$MF" "$BAD" 2>/dev/null || true

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

echo "PATCH=MULTIACTUATOR_REJECT_LEDGER_FIXED"
echo "HERMES_SYNTAX=OK"
echo "SHADOW_SYNTAX=OK"
echo "ACTIVE_BAD_ROWS=$(awk -F, 'NR>1&&NF!=11{n++}END{print n+0}' "$MF")"
echo "FORENSIC_BAD_ROWS=$(wc -l < "$BAD" 2>/dev/null || echo 0)"
