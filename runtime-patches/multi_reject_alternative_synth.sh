#!/system/bin/sh
set -u

R=/data/adb/djaeger_observer
M=/data/adb/modules/djaeger_ai_observer
H="$M/bin/hermes_adapter.sh"
S="$M/bin/shadow.sh"
W="$R/runtime/multi_reject_alternatives"
HN="$W/hermes.new"
SN="$W/shadow.new"
HELP="$W/helper.snip"
ALT="$W/alternatives.snip"
MP="$W/multipersist.snip"
mkdir -p "$W" || exit 1

cat > "$HELP" <<'EOF'
strategy_quarantined_file(){
  _qs="$1"
  _qf="$ROOT/history/shadow_reject_strategies.csv"
  [ -r "$_qf" ] || return 1
  _qn=$(date +%s)
  _qp=$(kv PACKAGE "$_qs")
  _qi=$(kv INTENT "$_qs")
  _qa=$(kv ACTUATORS "$_qs")
  _ql0=$(kv LITTLE_MIN_KHZ "$_qs"); _ql1=$(kv LITTLE_MAX_KHZ "$_qs")
  _qb0=$(kv BIG_MIN_KHZ "$_qs"); _qb1=$(kv BIG_MAX_KHZ "$_qs")
  _qg0=$(kv GPU_MIN_HZ "$_qs"); _qg1=$(kv GPU_MAX_HZ "$_qs")
  awk -F, -v now="$_qn" -v p="$_qp" -v i="$_qi" -v a="$_qa" \
    -v l0="$_ql0" -v l1="$_ql1" -v b0="$_qb0" -v b1="$_qb1" -v g0="$_qg0" -v g1="$_qg1" '
    NR>1 && $1~/^[0-9]+$/ && now-$1>=0 && now-$1<=900 &&
    $2==p && $3==i && $4==a && $5==l0 && $6==l1 &&
    $7==b0 && $8==b1 && $9==g0 && $10==g1 {found=1}
    END{exit !found}
  ' "$_qf" 2>/dev/null
}

rewrite_local_candidate_tmp(){
  {
    echo "PACKAGE=$_pkg"
    echo "INTENT=$_intent"
    echo "ACTUATORS=$_actuators"
    echo "LITTLE_MIN_KHZ=$_nl0"; echo "LITTLE_MAX_KHZ=$_nl1"
    echo "BIG_MIN_KHZ=$_nb0"; echo "BIG_MAX_KHZ=$_nb1"
    echo "GPU_MIN_HZ=$_ng0"; echo "GPU_MAX_HZ=$_ng1"
  } > "$_tmp"
}

EOF

cat > "$ALT" <<'EOF'
  # MULTI_REJECT_ALTERNATIVE_SYNTH
  # Never repeat a semantically identical shadow-rejected strategy during
  # the 900s quarantine. Try a different local actuator before giving up.
  if strategy_quarantined_file "$_tmp"; then
    if [ "$_actuators" = GPU ]; then
      _n=$(opp_prev_in_range "$_bav" "$_b1" "$_b0")
      if [ -n "$_n" ]; then
        _nl0="$_l0"; _nl1="$_l1"
        _nb0="$_b0"; _nb1="$_n"
        _ng0="$_g0"; _ng1="$_g1"
        _actuators=BIG
        if thermal_pressure; then
          _reason=LOCAL_HUMAN_COMFORT_THERMAL_TRIM_BIG
        else
          _reason=LOCAL_POWER_TRIM_BIG
        fi
        rewrite_local_candidate_tmp
      fi
    fi
  fi

  if strategy_quarantined_file "$_tmp"; then
    if [ "$_actuators" = BIG ] || [ "$_actuators" = GPU ]; then
      _n=$(opp_prev_in_range "$_lav" "$_l1" "$_l0")
      if [ -n "$_n" ]; then
        _nl0="$_l0"; _nl1="$_n"
        _nb0="$_b0"; _nb1="$_b1"
        _ng0="$_g0"; _ng1="$_g1"
        _actuators=LITTLE
        if thermal_pressure; then
          _reason=LOCAL_HUMAN_COMFORT_THERMAL_TRIM_LITTLE
        else
          _reason=LOCAL_POWER_TRIM_LITTLE
        fi
        rewrite_local_candidate_tmp
      fi
    fi
  fi

  if strategy_quarantined_file "$_tmp"; then
    rm -f "$_tmp" "$HPLAN" "$LOCAL_OUT"
    HDETAIL=all_local_comfort_strategies_quarantined
    return 1
  fi

EOF

cat > "$MP" <<'EOF'
  # PERSIST_REJECT_STRATEGY_MULTI
  case "$_reason" in
    human_comfort_contract_failed_*)
      _mf="$ROOT/history/shadow_reject_strategies.csv"
      if [ ! -r "$_mf" ]; then
        echo "AT,PACKAGE,INTENT,ACTUATORS,LITTLE_MIN_KHZ,LITTLE_MAX_KHZ,BIG_MIN_KHZ,BIG_MAX_KHZ,GPU_MIN_HZ,GPU_MAX_HZ,REASON" > "$_mf"
        chmod 600 "$_mf"
      fi
      _mp=$(kv PACKAGE "$POLICY")
      _mi=$(kv INTENT "$POLICY")
      _ma=$(kv ACTUATORS "$POLICY")
      _ml0=$(kv LITTLE_MIN_KHZ "$POLICY"); _ml1=$(kv LITTLE_MAX_KHZ "$POLICY")
      _mb0=$(kv BIG_MIN_KHZ "$POLICY"); _mb1=$(kv BIG_MAX_KHZ "$POLICY")
      _mg0=$(kv GPU_MIN_HZ "$POLICY"); _mg1=$(kv GPU_MAX_HZ "$POLICY")
      if ! awk -F, -v now="$_now" -v p="$_mp" -v i="$_mi" -v a="$_ma" \
        -v l0="$_ml0" -v l1="$_ml1" -v b0="$_mb0" -v b1="$_mb1" -v g0="$_mg0" -v g1="$_mg1" '
        NR>1 && $1~/^[0-9]+$/ && now-$1>=0 && now-$1<=900 &&
        $2==p && $3==i && $4==a && $5==l0 && $6==l1 &&
        $7==b0 && $8==b1 && $9==g0 && $10==g1 {found=1}
        END{exit !found}
      ' "$_mf" 2>/dev/null; then
        printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
          "$_now" "$_mp" "$_mi" "$_ma" "$_ml0" "$_ml1" \
          "$_mb0" "$_mb1" "$_mg0" "$_mg1" "$_reason" >> "$_mf"
      fi
      _mt="$_mf.tmp.$$"
      {
        head -n 1 "$_mf"
        tail -n +2 "$_mf" | tail -n 64
      } > "$_mt"
      chmod 600 "$_mt"
      mv -f "$_mt" "$_mf"
      ;;
  esac
EOF

# Add helper functions once, immediately before local_history_takeover.
if grep -Fq "strategy_quarantined_file(){" "$H"; then
  cp "$H" "$HN"
else
  awk -v SNIP="$HELP" '
    BEGIN{done=0}
    {
      if ($0 == "local_history_takeover(){" && !done) {
        while ((getline x < SNIP) > 0) print x
        close(SNIP)
        done=1
      }
      print
    }
    END{if(!done) exit 41}
  ' "$H" > "$HN" || exit 41
fi

# Replace the old single-env quarantine block with multi-strategy alternatives.
awk -v SNIP="$ALT" '
  BEGIN{skip=0; inserted=0}
  {
    if ($0 ~ /^  # PERSISTENT_SHADOW_REJECT_QUARANTINE/) {
      skip=1
      if(!inserted){
        while ((getline x < SNIP) > 0) print x
        close(SNIP)
        inserted=1
      }
      next
    }
    if(skip && $0 ~ /^  if ! validate_candidate_file "\$_tmp"; then/) {
      skip=0
      print
      next
    }
    if(skip) next
    print
  }
  END{
    if(!inserted) exit 42
  }
' "$HN" > "$W/hermes.alt" || exit 42
mv -f "$W/hermes.alt" "$HN"

# Expand observe barrier to include the "all alternatives rejected" state.
sed 's/if \[ "\$HDETAIL" = shadow_rejected_strategy_quarantine \]; then/case "$HDETAIL" in shadow_rejected_strategy_quarantine|all_local_comfort_strategies_quarantined) true;; *) false;; esac; if [ $? -eq 0 ]; then/'   "$HN" > "$W/hermes.barrier" || exit 43
mv -f "$W/hermes.barrier" "$HN"

# Add multi reject persistence without removing the existing single reject env.
if grep -Fq "PERSIST_REJECT_STRATEGY_MULTI" "$S"; then
  cp "$S" "$SN"
else
  awk -v SNIP="$MP" '
    BEGIN{done=0}
    {
      print
      if ($0 ~ /^  # PERSIST_REJECT_STRATEGY$/ && !done) {
        # Insert multi persistence before the existing single-file block.
        while ((getline x < SNIP) > 0) print x
        close(SNIP)
        done=1
      }
    }
    END{if(!done) exit 44}
  ' "$S" > "$SN" || exit 44
fi

sh -n "$HN" || exit 51
sh -n "$SN" || exit 52

# Seed the multi ledger from the already proven GPU rejection.
MF="$R/history/shadow_reject_strategies.csv"
if [ ! -r "$MF" ]; then
  echo "AT,PACKAGE,INTENT,ACTUATORS,LITTLE_MIN_KHZ,LITTLE_MAX_KHZ,BIG_MIN_KHZ,BIG_MAX_KHZ,GPU_MIN_HZ,GPU_MAX_HZ,REASON" > "$MF"
fi
RJ="$R/history/shadow_reject_strategy.env"
if [ -r "$RJ" ]; then
  AT=$(sed -n 's/^AT=//p' "$RJ" | head -n1)
  PK=$(sed -n 's/^PACKAGE=//p' "$RJ" | head -n1)
  IN=$(sed -n 's/^INTENT=//p' "$RJ" | head -n1)
  AC=$(sed -n 's/^ACTUATORS=//p' "$RJ" | head -n1)
  L0=$(sed -n 's/^LITTLE_MIN_KHZ=//p' "$RJ" | head -n1)
  L1=$(sed -n 's/^LITTLE_MAX_KHZ=//p' "$RJ" | head -n1)
  B0=$(sed -n 's/^BIG_MIN_KHZ=//p' "$RJ" | head -n1)
  B1=$(sed -n 's/^BIG_MAX_KHZ=//p' "$RJ" | head -n1)
  G0=$(sed -n 's/^GPU_MIN_HZ=//p' "$RJ" | head -n1)
  G1=$(sed -n 's/^GPU_MAX_HZ=//p' "$RJ" | head -n1)
  RR=$(sed -n 's/^REASON=//p' "$RJ" | head -n1)
  if ! grep -Fq ",$PK,$IN,$AC,$L0,$L1,$B0,$B1,$G0,$G1," "$MF" 2>/dev/null; then
    printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" "$AT" "$PK" "$IN" "$AC" "$L0" "$L1" "$B0" "$B1" "$G0" "$G1" "$RR" >> "$MF"
  fi
fi
chmod 600 "$MF"

TS=$(date +%s)
cp "$H" "$R/runtime/hermes_adapter.pre_multi_reject.$TS" || exit 61
cp "$S" "$R/runtime/shadow.pre_multi_reject.$TS" || exit 62
cp "$HN" "$H" || exit 63
cp "$SN" "$S" || exit 64
chmod 755 "$H" "$S"

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

echo "PATCH=MULTI_REJECT_ALTERNATIVE_SYNTH_ACTIVE"
echo "HERMES_SYNTAX=OK"
echo "SHADOW_SYNTAX=OK"
