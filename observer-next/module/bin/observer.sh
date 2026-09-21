#!/system/bin/sh
ROOT="$1"
RUNTIME="$ROOT/runtime"
HISTORY="$ROOT/history/telemetry.csv"
SNAP="$RUNTIME/snapshot.env"
SEQ=0
PKG=UNKNOWN

read_one() {
  for p in "$@"; do
    [ -r "$p" ] || continue
    v=$(cat "$p" 2>/dev/null | head -n1)
    [ -n "$v" ] && { echo "$v"; return; }
  done
  echo "NA"
}

temp_c() {
  v="$1"
  case "$v" in ''|NA|*[!0-9-]*) echo "NA"; return;; esac
  awk -v x="$v" 'BEGIN{if(x>1000||x<-1000) printf "%.1f",x/1000; else if(x>200) printf "%.1f",x/10; else printf "%.1f",x}'
}

thermal_by_type() {
  pat="$1"
  for z in /sys/class/thermal/thermal_zone*; do
    [ -r "$z/type" ] || continue
    t=$(cat "$z/type" 2>/dev/null)
    echo "$t" | grep -Eqi "$pat" || continue
    read_one "$z/temp"
    return
  done
  echo "NA"
}

gpu_path() {
  for p in /sys/class/kgsl/kgsl-3d0/devfreq /sys/class/devfreq/*gpu* /sys/class/devfreq/*mali*; do
    [ -d "$p" ] || continue
    [ -r "$p/cur_freq" ] || continue
    echo "$p"
    return
  done
  echo ""
}

mkdir -p "$RUNTIME" "$ROOT/history"
if [ -f "$HISTORY" ] && ! head -n1 "$HISTORY" 2>/dev/null | grep -q 'little_cur_khz'; then
  mv -f "$HISTORY" "$ROOT/history/telemetry.v1.$(date +%s).csv" 2>/dev/null
fi
[ -f "$HISTORY" ] || echo "epoch,seq,package,cpu_avg_khz,cpu_min_cur_khz,cpu_max_cur_khz,little_cur_khz,big_cur_khz,gpu_cur_hz,skin_c,battery_c,current_ua,voltage_uv,power_mw,battery_pct" > "$HISTORY"

LOW_POLICY=""
HIGH_POLICY=""
for p in /sys/devices/system/cpu/cpufreq/policy*; do
  [ -d "$p" ] || continue
  [ -z "$LOW_POLICY" ] && LOW_POLICY="$p"
  HIGH_POLICY="$p"
done
GPU_PATH=$(gpu_path)

while true; do
  SEQ=$((SEQ+1))
  EPOCH=$(date +%s)

  SUM=0; CNT=0; MIN=0; MAX=0; VECTOR=""
  for f in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq; do
    [ -r "$f" ] || continue
    v=$(cat "$f" 2>/dev/null)
    case "$v" in ''|*[!0-9]*) continue;; esac
    SUM=$((SUM+v)); CNT=$((CNT+1))
    if [ "$MIN" -eq 0 ] || [ "$v" -lt "$MIN" ]; then MIN=$v; fi
    [ "$v" -gt "$MAX" ] && MAX=$v
    [ -z "$VECTOR" ] && VECTOR="$v" || VECTOR="$VECTOR,$v"
  done
  [ "$CNT" -gt 0 ] && AVG=$((SUM/CNT)) || AVG=0

  LITTLE=$(read_one "$LOW_POLICY/scaling_cur_freq")
  BIG=$(read_one "$HIGH_POLICY/scaling_cur_freq")
  GPU=$(read_one "$GPU_PATH/cur_freq" /sys/class/kgsl/kgsl-3d0/gpuclk)
  GLOAD=$(read_one /sys/class/kgsl/kgsl-3d0/gpubusy "$GPU_PATH/load")

  SKIN=$(temp_c "$(thermal_by_type 'skin|shell|surface|quiet')")
  CPUC=$(temp_c "$(thermal_by_type 'cpu|soc|ap|tsens')")
  GPUC=$(temp_c "$(thermal_by_type 'gpu')")
  BATC=$(temp_c "$(read_one /sys/class/power_supply/battery/temp)")
  CUR=$(read_one /sys/class/power_supply/battery/current_now)
  VOLT=$(read_one /sys/class/power_supply/battery/voltage_now)
  PCT=$(read_one /sys/class/power_supply/battery/capacity)

  POWER=NA
  case "$CUR:$VOLT" in
    *[!0-9:-]*|NA:*|*:NA) ;;
    *) POWER=$(awk -v a="$CUR" -v v="$VOLT" 'BEGIN{if(a<0)a=-a; printf "%.0f",(a*v)/1000000000}') ;;
  esac

  if [ $((SEQ % 5)) -eq 1 ]; then
    PKG=$(dumpsys activity activities 2>/dev/null | grep -m1 'mResumedActivity' | sed -n 's/.* u[0-9]* \([^/ ]*\)\/.*/\1/p')
    [ -n "$PKG" ] || PKG=UNKNOWN
  fi

  MIGRATION_STATE=$(grep '^MIGRATION_STATE=' "$ROOT/recovery/migration.env" 2>/dev/null | cut -d= -f2-)
  LEGACY_CONFIG_PRESENT=$(grep '^LEGACY_CONFIG_PRESENT=' "$ROOT/recovery/migration.env" 2>/dev/null | cut -d= -f2-)
  [ -n "$MIGRATION_STATE" ] || MIGRATION_STATE=UNKNOWN
  [ -n "$LEGACY_CONFIG_PRESENT" ] || LEGACY_CONFIG_PRESENT=NO

  PKG_SAMPLES=$(awk -F, -v p="$PKG" 'NR>1&&$3==p{n++}END{print n+0}' "$HISTORY" 2>/dev/null)
  if [ "$PKG_SAMPLES" -ge 600 ]; then LEARN=BASELINE_MATURE
  elif [ "$PKG_SAMPLES" -ge 120 ]; then LEARN=BASELINE_READY
  else LEARN=LEARNING
  fi

  TMP="$SNAP.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_OBSERVER_V2"
    echo "ENGINE=OBSERVER_FIRST"
    echo "MODULE_VERSION=0.2.0-observer"
    echo "SAMPLE_SEQ=$SEQ"
    echo "PACKAGE_SAMPLES=$PKG_SAMPLES"
    echo "EPOCH=$EPOCH"
    echo "ACTIVE_PACKAGE=$PKG"
    echo "CPU_AVG_KHZ=$AVG"
    echo "CPU_CUR_MIN_KHZ=$MIN"
    echo "CPU_CUR_MAX_KHZ=$MAX"
    echo "CPU_VECTOR_KHZ=$VECTOR"
    echo "LITTLE_CUR_KHZ=$LITTLE"
    echo "BIG_CUR_KHZ=$BIG"
    echo "LITTLE_POLICY_PATH=$LOW_POLICY"
    echo "BIG_POLICY_PATH=$HIGH_POLICY"
    echo "GPU_CUR_HZ=$GPU"
    echo "GPU_LOAD_RAW=$GLOAD"
    echo "GPU_DEVFREQ_PATH=$GPU_PATH"
    echo "SKIN_TEMP_C=$SKIN"
    echo "CPU_TEMP_C=$CPUC"
    echo "GPU_TEMP_C=$GPUC"
    echo "BATTERY_TEMP_C=$BATC"
    echo "BATTERY_CURRENT_UA=$CUR"
    echo "BATTERY_VOLTAGE_UV=$VOLT"
    echo "POWER_MW=$POWER"
    echo "BATTERY_PCT=$PCT"
    echo "FRAME_EVIDENCE=UNAVAILABLE"
    echo "LEARNING_STATE=$LEARN"
    echo "MIGRATION_STATE=$MIGRATION_STATE"
    echo "LEGACY_CONFIG_PRESENT=$LEGACY_CONFIG_PRESENT"
    echo "LEGACY_PROFILES=DISABLED"
    echo "HARDWARE_AUTHORITY=VALIDATED_EXECUTOR_ONLY"
  } > "$TMP"
  chmod 644 "$TMP"
  mv -f "$TMP" "$SNAP"

  echo "$EPOCH,$SEQ,$PKG,$AVG,$MIN,$MAX,$LITTLE,$BIG,$GPU,$SKIN,$BATC,$CUR,$VOLT,$POWER,$PCT" >> "$HISTORY"

  SIZE=$(wc -c < "$HISTORY" 2>/dev/null)
  case "$SIZE" in ''|*[!0-9]*) SIZE=0;; esac
  if [ "$SIZE" -gt 2097152 ]; then
    { head -n1 "$HISTORY"; tail -n 5000 "$HISTORY"; } > "$HISTORY.trim"
    mv -f "$HISTORY.trim" "$HISTORY"
  fi
  sleep 2
done
