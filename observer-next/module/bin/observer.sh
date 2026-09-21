#!/system/bin/sh
ROOT="$1"
MODDIR="$2"
RUNTIME="$ROOT/runtime"
HISTORY="$ROOT/history/telemetry.csv"
SNAP="$RUNTIME/snapshot.env"
FRAMEFILE="$RUNTIME/frame.env"
SEQ=0
PKG=UNKNOWN
PKG_SAMPLES=0
LAST_COUNT_PKG=""
PUBLISHER_READY=0
if [ -r "$MODDIR/bin/publisher.sh" ]; then
  . "$MODDIR/bin/publisher.sh"
  PUBLISHER_READY=1
fi

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

fv(){ sed -n "s/^$1=//p" "$FRAMEFILE" 2>/dev/null | head -n1; }

mkdir -p "$RUNTIME" "$ROOT/history"
if [ -f "$HISTORY" ] && ! head -n1 "$HISTORY" 2>/dev/null | grep -q 'frame_at'; then
  mv -f "$HISTORY" "$ROOT/history/telemetry.preframe.$(date +%s).csv" 2>/dev/null
fi
[ -f "$HISTORY" ] || echo "epoch,seq,package,cpu_avg_khz,cpu_min_cur_khz,cpu_max_cur_khz,little_cur_khz,big_cur_khz,gpu_cur_hz,skin_c,battery_c,current_ua,voltage_uv,power_mw,battery_pct,fps,jank_pct,p95_ms,p99_ms,frame_n,frame_at,battery_status" > "$HISTORY"

LOW_POLICY=""
HIGH_POLICY=""
for p in /sys/devices/system/cpu/cpufreq/policy*; do
  [ -d "$p" ] || continue
  [ -z "$LOW_POLICY" ] && LOW_POLICY="$p"
  HIGH_POLICY="$p"
done
GPU_PATH=$(gpu_path)
LITTLE_AVAILABLE=$(read_one "$LOW_POLICY/scaling_available_frequencies")
BIG_AVAILABLE=$(read_one "$HIGH_POLICY/scaling_available_frequencies")
GPU_AVAILABLE=$(read_one "$GPU_PATH/available_frequencies" /sys/class/kgsl/kgsl-3d0/devfreq/available_frequencies)

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
  BSTAT=$(read_one /sys/class/power_supply/battery/status)

  POWER=NA
  case "$CUR:$VOLT:$BSTAT" in
    *[!0-9:A-Za-z_-]*|NA:*|*:NA:*|*:*:NA) ;;
    *)
      if [ "$BSTAT" = Discharging ]; then
        POWER=$(awk -v a="$CUR" -v v="$VOLT" 'BEGIN{
          if(a<0)a=-a
          p=(a*v)/1000000000
          if(p>=100&&p<=15000){printf "%.0f",p;exit}
          if(a>=20&&a<=5000){p=(a*1000*v)/1000000000;if(p>=100&&p<=15000){printf "%.0f",p;exit}}
          print "NA"
        }')
      fi
    ;;
  esac

  if [ $((SEQ % 2)) -eq 1 ]; then
    PKG=$(dumpsys activity activities 2>/dev/null | grep -m1 'mResumedActivity' | sed -n 's/.* u[0-9]* \([^/ ]*\)\/.*/\1/p')
    [ -n "$PKG" ] || PKG=UNKNOWN
  fi

  FE=UNAVAILABLE; FPS=NA; JANK=NA; P95=NA; P99=NA; FN=0; FAT=0
  if [ -r "$FRAMEFILE" ] && [ "$(fv FRAME_PACKAGE)" = "$PKG" ]; then
    FAT=$(fv FRAME_AT); case "$FAT" in ''|*[!0-9]*) FAT=0;; esac
    FAGE=$((EPOCH-FAT))
    if [ "$FAGE" -ge 0 ] && [ "$FAGE" -le 10 ]; then
      FE=$(fv FRAME_EVIDENCE)
      FPS=$(fv FPS_EST); JANK=$(fv JANK_PCT); P95=$(fv P95_MS); P99=$(fv P99_MS); FN=$(fv FRAME_N)
      [ -n "$FPS" ] || FPS=NA; [ -n "$JANK" ] || JANK=NA; [ -n "$P95" ] || P95=NA; [ -n "$P99" ] || P99=NA
      case "$FN" in ''|*[!0-9]*) FN=0;; esac
    fi
  fi

  MIGRATION_STATE=$(grep '^MIGRATION_STATE=' "$ROOT/recovery/migration.env" 2>/dev/null | cut -d= -f2-)
  LEGACY_CONFIG_PRESENT=$(grep '^LEGACY_CONFIG_PRESENT=' "$ROOT/recovery/migration.env" 2>/dev/null | cut -d= -f2-)
  [ -n "$MIGRATION_STATE" ] || MIGRATION_STATE=UNKNOWN
  [ -n "$LEGACY_CONFIG_PRESENT" ] || LEGACY_CONFIG_PRESENT=NO

  if [ "$PKG" != "$LAST_COUNT_PKG" ] || [ $((SEQ % 5)) -eq 1 ]; then
    PKG_SAMPLES=$(awk -F, -v p="$PKG" 'NR>1&&$3==p{n++}END{print n+0}' "$HISTORY" 2>/dev/null)
    LAST_COUNT_PKG="$PKG"
  else
    PKG_SAMPLES=$((PKG_SAMPLES+1))
  fi
  if [ "$PKG_SAMPLES" -ge 600 ]; then LEARN=BASELINE_CPU_MATURE
  elif [ "$PKG_SAMPLES" -ge 120 ]; then LEARN=BASELINE_CPU_READY
  else LEARN=LEARNING
  fi

  TMP="$SNAP.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_OBSERVER_V3"
    echo "ENGINE=OBSERVER_FIRST"
    echo "MODULE_VERSION=0.2.1-observer-next"
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
    echo "LITTLE_AVAILABLE_KHZ=$LITTLE_AVAILABLE"
    echo "BIG_AVAILABLE_KHZ=$BIG_AVAILABLE"
    echo "GPU_CUR_HZ=$GPU"
    echo "GPU_LOAD_RAW=$GLOAD"
    echo "GPU_DEVFREQ_PATH=$GPU_PATH"
    echo "GPU_AVAILABLE_HZ=$GPU_AVAILABLE"
    echo "SKIN_TEMP_C=$SKIN"
    echo "CPU_TEMP_C=$CPUC"
    echo "GPU_TEMP_C=$GPUC"
    echo "BATTERY_TEMP_C=$BATC"
    echo "BATTERY_CURRENT_UA=$CUR"
    echo "BATTERY_VOLTAGE_UV=$VOLT"
    echo "BATTERY_STATUS=$BSTAT"
    echo "POWER_MW=$POWER"
    echo "BATTERY_PCT=$PCT"
    echo "FRAME_EVIDENCE=$FE"
    echo "FPS_EST=$FPS"
    echo "JANK_PCT=$JANK"
    echo "P95_MS=$P95"
    echo "P99_MS=$P99"
    echo "FRAME_N=$FN"
    echo "FRAME_AT=$FAT"
    echo "LEARNING_STATE=$LEARN"
    echo "MIGRATION_STATE=$MIGRATION_STATE"
    echo "LEGACY_CONFIG_PRESENT=$LEGACY_CONFIG_PRESENT"
    echo "LEGACY_PROFILES=DISABLED"
    echo "HARDWARE_AUTHORITY=STOCK_KERNEL_READ_ONLY"
  } > "$TMP"
  chmod 644 "$TMP"
  mv -f "$TMP" "$SNAP"

  echo "$EPOCH,$SEQ,$PKG,$AVG,$MIN,$MAX,$LITTLE,$BIG,$GPU,$SKIN,$BATC,$CUR,$VOLT,$POWER,$PCT,$FPS,$JANK,$P95,$P99,$FN,$FAT,$BSTAT" >> "$HISTORY"

  SIZE=$(wc -c < "$HISTORY" 2>/dev/null)
  case "$SIZE" in ''|*[!0-9]*) SIZE=0;; esac
  if [ "$SIZE" -gt 3145728 ]; then
    { head -n1 "$HISTORY"; tail -n 7500 "$HISTORY"; } > "$HISTORY.trim"
    mv -f "$HISTORY.trim" "$HISTORY"
  fi
  [ "$PUBLISHER_READY" = 1 ] && publish_cc "$ROOT"
  WORKLOAD_CLASS=$(sed -n 's/^WORKLOAD_CLASS=//p' "$ROOT/runtime/workload.env" 2>/dev/null | head -n1)
  [ "$WORKLOAD_CLASS" = GAME ] && sleep 3 || sleep 10
done
