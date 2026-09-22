#!/system/bin/sh
ROOT="$1"
BIN_DIR="${0%/*}"
if [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim learner
fi
HISTORY="$ROOT/history/telemetry.csv"
SNAP="$ROOT/runtime/snapshot.env"
OUT="$ROOT/history/learned_envelope.env"
OUTCOMES="$ROOT/history/outcomes.csv"
TMPBASE="$ROOT/runtime/learner.$$"
WORKLOAD="$ROOT/runtime/workload.env"
LAST_PKG=""
LAST_N=0

qcol() {
  pkg="$1"; col="$2"; pct="$3"; tmp="$TMPBASE.i.$col.$pct"
  awk -F, -v p="$pkg" -v c="$col" 'NR>1 && $3==p && $23=="STOCK_BASELINE" && $c ~ /^[0-9]+$/ && $c>0 {print $c}' "$HISTORY" 2>/dev/null | sort -n > "$tmp"
  n=$(wc -l < "$tmp" 2>/dev/null)
  case "$n" in ''|0) rm -f "$tmp"; echo 0; return;; esac
  idx=$(( (n*pct + 99) / 100 ))
  [ "$idx" -lt 1 ] && idx=1
  [ "$idx" -gt "$n" ] && idx="$n"
  sed -n "${idx}p" "$tmp"
  rm -f "$tmp"
}

qframe() {
  pkg="$1"; col="$2"; pct="$3"; tmp="$TMPBASE.f.$col.$pct"
  awk -F, -v p="$pkg" -v c="$col" '
    NR>1 && $3==p && $23=="STOCK_BASELINE" && $20+0>=20 && $21 ~ /^[0-9]+$/ && !seen[$21]++ &&
    $c ~ /^[0-9]+([.][0-9]+)?$/ && $c>=0 {print $c}
  ' "$HISTORY" 2>/dev/null | sort -n > "$tmp"
  n=$(wc -l < "$tmp" 2>/dev/null)
  case "$n" in ''|0) rm -f "$tmp"; echo 0; return;; esac
  idx=$(( (n*pct + 99) / 100 ))
  [ "$idx" -lt 1 ] && idx=1
  [ "$idx" -gt "$n" ] && idx="$n"
  sed -n "${idx}p" "$tmp"
  rm -f "$tmp"
}

while true; do
  [ -r "$SNAP" ] && [ -r "$HISTORY" ] || { sleep 15; continue; }
  PKG=$(sed -n 's/^ACTIVE_PACKAGE=//p' "$SNAP" | head -n1)
  WPKG=$(sed -n 's/^PACKAGE=//p' "$WORKLOAD" 2>/dev/null | head -n1)
  WCLASS=$(sed -n 's/^WORKLOAD_CLASS=//p' "$WORKLOAD" 2>/dev/null | head -n1)
  [ "$WCLASS" = GAME ] && [ "$WPKG" = "$PKG" ] || { sleep 30; continue; }

  N=$(awk -F, -v p="$PKG" 'NR>1&&$3==p&&$23=="STOCK_BASELINE"{n++}END{print n+0}' "$HISTORY" 2>/dev/null)
  [ "$N" -ge 120 ] 2>/dev/null || { sleep 30; continue; }
  if [ "$PKG" = "$LAST_PKG" ] && [ "$N" -lt $((LAST_N+20)) ] 2>/dev/null; then
    sleep 30
    continue
  fi

  FN=$(awk -F, -v p="$PKG" 'NR>1&&$3==p&&$23=="STOCK_BASELINE"&&$20+0>=20&&$21~/^[0-9]+$/&&!seen[$21]++{n++}END{print n+0}' "$HISTORY" 2>/dev/null)

  L05=$(qcol "$PKG" 7 5); L95=$(qcol "$PKG" 7 95)
  B05=$(qcol "$PKG" 8 5); B95=$(qcol "$PKG" 8 95)
  G05=$(qcol "$PKG" 9 5); G95=$(qcol "$PKG" 9 95)
  P50=$(qcol "$PKG" 14 50); P95=$(qcol "$PKG" 14 95)

  FPS50=0; JANK95=0; FP95=0; FP99=0
  if [ "$FN" -gt 0 ]; then
    FPS50=$(qframe "$PKG" 16 50)
    JANK95=$(qframe "$PKG" 17 95)
    FP95=$(qframe "$PKG" 18 95)
    FP99=$(qframe "$PKG" 19 95)
  fi

  [ "$L05" -gt 0 ] && [ "$L95" -ge "$L05" ] || { sleep 20; continue; }
  [ "$B05" -gt 0 ] && [ "$B95" -ge "$B05" ] || { sleep 20; continue; }
  [ "$G05" -gt 0 ] && [ "$G95" -ge "$G05" ] || { sleep 20; continue; }

  FRAME_STATE=INSUFFICIENT
  [ "$FN" -ge 120 ] && FRAME_STATE=VALID

  if [ "$N" -ge 600 ] && [ "$FN" -ge 120 ]; then
    STATE=READY_HARDWARE_MODEL
    CONF=$((75 + (N-600)/80 + (FN-120)/24))
    [ "$CONF" -gt 95 ] && CONF=95
  elif [ "$N" -ge 600 ]; then
    STATE=BASELINE_FRAME_PENDING
    CONF=70
  else
    STATE=BASELINE_READY
    CONF=$((50 + (N-120)*20/480))
  fi

  OUTCOME_ROWS=0; KEEP_ROWS=0; ROLLBACK_ROWS=0; OUTCOME_FEEDBACK=NONE; LAST_OUTCOME=NONE; LAST_OUTCOME_REASON=NONE
  if [ -r "$OUTCOMES" ]; then
    OUTCOME_ROWS=$(awk -F, -v p="$PKG" 'NR>1&&$2==p{n++}END{print n+0}' "$OUTCOMES" 2>/dev/null)
    KEEP_ROWS=$(awk -F, -v p="$PKG" 'NR>1&&$2==p&&($4=="KEPT"||$4=="APPLIED_VERIFIED"){n++}END{print n+0}' "$OUTCOMES" 2>/dev/null)
    ROLLBACK_ROWS=$(awk -F, -v p="$PKG" 'NR>1&&$2==p&&($4=="ROLLED_BACK"||$4=="ROLLBACK_FAILED"){n++}END{print n+0}' "$OUTCOMES" 2>/dev/null)
    LAST_OUTCOME=$(awk -F, -v p="$PKG" 'NR>1&&$2==p{v=$4}END{print v}' "$OUTCOMES" 2>/dev/null); [ -n "$LAST_OUTCOME" ] || LAST_OUTCOME=NONE
    LAST_OUTCOME_REASON=$(awk -F, -v p="$PKG" 'NR>1&&$2==p{v=$5}END{print v}' "$OUTCOMES" 2>/dev/null); [ -n "$LAST_OUTCOME_REASON" ] || LAST_OUTCOME_REASON=NONE
    if [ "$ROLLBACK_ROWS" -gt "$KEEP_ROWS" ] 2>/dev/null && [ "$OUTCOME_ROWS" -ge 3 ] 2>/dev/null; then
      OUTCOME_FEEDBACK=CAUTION
      [ "$CONF" -le 75 ] || CONF=75
    elif [ "$KEEP_ROWS" -ge 3 ] 2>/dev/null; then
      OUTCOME_FEEDBACK=STABLE
    fi
  fi

  T="$OUT.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_LEARNED_ENVELOPE_V3"
    echo "AT=$(date +%s)"
    echo "PACKAGE=$PKG"
    echo "STATE=$STATE"
    echo "SAMPLES=$N"
    echo "FRAME_WINDOWS=$FN"
    echo "CONFIDENCE=$CONF"
    echo "LITTLE_MIN_KHZ=$L05"
    echo "LITTLE_MAX_KHZ=$L95"
    echo "BIG_MIN_KHZ=$B05"
    echo "BIG_MAX_KHZ=$B95"
    echo "GPU_MIN_HZ=$G05"
    echo "GPU_MAX_HZ=$G95"
    echo "POWER_P50_MW=$P50"
    echo "POWER_P95_MW=$P95"
    echo "FRAME_EVIDENCE=$FRAME_STATE"
    echo "FPS_P50=$FPS50"
    echo "JANK_P95=$JANK95"
    echo "FRAME_P95_P95_MS=$FP95"
    echo "FRAME_P99_P95_MS=$FP99"
    echo "OUTCOME_ROWS=$OUTCOME_ROWS"
    echo "KEEP_ROWS=$KEEP_ROWS"
    echo "ROLLBACK_ROWS=$ROLLBACK_ROWS"
    echo "OUTCOME_FEEDBACK=$OUTCOME_FEEDBACK"
    echo "LAST_OUTCOME=$LAST_OUTCOME"
    echo "LAST_OUTCOME_REASON=$LAST_OUTCOME_REASON"
    echo "SOURCE=STOCK_BASELINE_ONLY_P05_P95_PLUS_SURFACEFLINGER"
  } > "$T"
  chmod 600 "$T"
  mv -f "$T" "$OUT"
  LAST_PKG="$PKG"
  LAST_N="$N"
  sleep 60
done
