#!/system/bin/sh
# DJAEGER AI read-only network telemetry worker.
# Measures generic connectivity only. It never changes routing, DNS, VPN,
# OpenClash, sockets, game traffic, or kernel network settings.

ROOT="$1"
MODDIR="$2"
BIN_DIR="${0%/*}"
if [ -r "$BIN_DIR/singleton.sh" ]; then
  . "$BIN_DIR/singleton.sh"
  djaeger_singleton_claim network_observer
fi

RUNTIME="$ROOT/runtime"
WORKLOAD="$RUNTIME/workload.env"
OUT="$RUNTIME/network.env"
CFG="$ROOT/config/network_probe.env"
mkdir -p "$RUNTIME"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }

publish_inactive(){
  _tmp="$OUT.tmp.$$"
  {
    echo "SESSION_ACTIVE=0"
    echo "QUALITY=INACTIVE"
    echo "SOURCE=READ_ONLY_ICMP_PROBE"
    echo "UPDATED_AT=$(date +%s)"
  } > "$_tmp"
  chmod 600 "$_tmp" 2>/dev/null
  mv -f "$_tmp" "$OUT"
}

while true; do
  WCLASS="$(kv WORKLOAD_CLASS "$WORKLOAD")"
  PKG="$(kv PACKAGE "$WORKLOAD")"
  if [ "$WCLASS" != GAME ] || [ -z "$PKG" ] || [ "$PKG" = UNKNOWN ]; then
    publish_inactive
    sleep 15
    continue
  fi

  TARGET="$(kv TARGET "$CFG")"
  [ -n "$TARGET" ] || TARGET=1.1.1.1
  case "$TARGET" in *[!0-9A-Za-z.:-]*) TARGET=1.1.1.1;; esac

  RAW="$RUNTIME/.network_ping.$$"
  TIMES="$RUNTIME/.network_times.$$"
  : > "$RAW"; : > "$TIMES"

  if command -v timeout >/dev/null 2>&1; then
    timeout 8 ping -c 5 -W 1 "$TARGET" > "$RAW" 2>/dev/null || true
  else
    ping -c 5 -W 1 "$TARGET" > "$RAW" 2>/dev/null || true
  fi

  sed -n 's/.*time=\([0-9][0-9.]*\)[[:space:]]*ms.*/\1/p' "$RAW" > "$TIMES"
  RECV="$(awk 'NF{n++}END{print n+0}' "$TIMES")"
  SENT=5
  LOSS=$(( (SENT-RECV)*100/SENT ))

  CUR=NA; AVG=NA; P95=NA; JITTER=NA
  if [ "$RECV" -gt 0 ]; then
    CUR="$(tail -n1 "$TIMES")"
    AVG="$(awk '{s+=$1;n++}END{if(n)printf "%.1f",s/n;else print "NA"}' "$TIMES")"
    P95="$(sort -n "$TIMES" | tail -n1)"
    JITTER="$(awk 'NR==1{p=$1;next}{d=$1-p;if(d<0)d=-d;s+=d;n++;p=$1}END{if(n)printf "%.1f",s/n;else printf "0.0"}' "$TIMES")"
  fi

  QUALITY=GOOD
  if [ "$RECV" -eq 0 ]; then
    QUALITY=PROBE_BLOCKED_OR_OFFLINE
  elif [ "$LOSS" -ge 10 ] 2>/dev/null || awk -v p="$P95" 'BEGIN{exit !(p>=150)}'; then
    QUALITY=BAD
  elif [ "$LOSS" -ge 3 ] 2>/dev/null || awk -v p="$P95" -v j="$JITTER" 'BEGIN{exit !(p>=80 || j>=20)}'; then
    QUALITY=FAIR
  fi

  TMP="$OUT.tmp.$$"
  {
    echo "SESSION_ACTIVE=1"
    echo "PACKAGE=$PKG"
    echo "PROBE_TARGET=$TARGET"
    echo "PING_CURRENT_MS=$CUR"
    echo "PING_AVG_MS=$AVG"
    echo "PING_P95_MS=$P95"
    echo "JITTER_MS=$JITTER"
    echo "PACKET_LOSS_PCT=$LOSS"
    echo "QUALITY=$QUALITY"
    echo "SOURCE=READ_ONLY_ICMP_PROBE"
    echo "UPDATED_AT=$(date +%s)"
  } > "$TMP"
  chmod 600 "$TMP" 2>/dev/null
  mv -f "$TMP" "$OUT"

  rm -f "$RAW" "$TIMES"
  sleep 12
done
