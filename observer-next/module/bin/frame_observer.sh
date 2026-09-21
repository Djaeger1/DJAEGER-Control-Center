#!/system/bin/sh
ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
OUT="$ROOT/runtime/frame.env"
CACHE="$ROOT/runtime/frame_layer.env"
WORKLOAD="$ROOT/runtime/workload.env"

capture(){
  if command -v timeout >/dev/null 2>&1; then
    timeout 2 "$@"
  else
    "$@"
  fi
}

publish_unavailable(){
  t="$OUT.tmp.$$"
  {
    echo "FRAME_EVIDENCE=UNAVAILABLE"
    echo "FRAME_REASON=$1"
    echo "FRAME_PACKAGE=$2"
    echo "FRAME_AT=$(date +%s)"
    echo "FPS_EST=NA"
    echo "JANK_PCT=NA"
    echo "P95_MS=NA"
    echo "P99_MS=NA"
    echo "FRAME_N=0"
  } > "$t"
  chmod 644 "$t"; mv -f "$t" "$OUT"
}

while true; do
  [ -r "$SNAP" ] || { sleep 5; continue; }
  PKG=$(sed -n 's/^ACTIVE_PACKAGE=//p' "$SNAP" | head -n1)
  WPKG=$(sed -n 's/^PACKAGE=//p' "$WORKLOAD" 2>/dev/null | head -n1)
  WCLASS=$(sed -n 's/^WORKLOAD_CLASS=//p' "$WORKLOAD" 2>/dev/null | head -n1)
  if [ "$WCLASS" != GAME ] || [ "$WPKG" != "$PKG" ]; then
    publish_unavailable NON_GAME_WORKLOAD "${PKG:-UNKNOWN}"
    sleep 15
    continue
  fi

  LAYER=""
  if [ -r "$CACHE" ] && [ "$(sed -n 's/^PACKAGE=//p' "$CACHE" | head -n1)" = "$PKG" ]; then
    LAYER=$(sed -n 's/^LAYER=//p' "$CACHE" | head -n1)
  fi

  if [ -z "$LAYER" ]; then
    LIST="$ROOT/runtime/.sf_list.$$"
    capture dumpsys SurfaceFlinger --list > "$LIST" 2>/dev/null || {
      rm -f "$LIST"
      publish_unavailable SURFACEFLINGER_LIST_TIMEOUT "$PKG"
      sleep 10
      continue
    }
    LAYER=$(grep -F "$PKG" "$LIST" | grep -F "SurfaceView[" | grep -F "(BLAST)" | head -n1)
    [ -n "$LAYER" ] || LAYER=$(grep -F "$PKG" "$LIST" | grep -F "(BLAST)" | head -n1)
    [ -n "$LAYER" ] || LAYER=$(grep -F "$PKG" "$LIST" | head -n1)
    rm -f "$LIST"
    if [ -z "$LAYER" ]; then
      rm -f "$CACHE"
      publish_unavailable LAYER_NOT_FOUND "$PKG"
      sleep 10
      continue
    fi
    {
      echo "PACKAGE=$PKG"
      echo "LAYER=$LAYER"
    } > "$CACHE.tmp.$$"
    chmod 600 "$CACHE.tmp.$$"; mv -f "$CACHE.tmp.$$" "$CACHE"
  fi

  RAW="$ROOT/runtime/.sf_latency.$$"
  capture dumpsys SurfaceFlinger --latency "$LAYER" > "$RAW" 2>/dev/null || {
    rm -f "$RAW" "$CACHE"
    publish_unavailable SURFACEFLINGER_LATENCY_TIMEOUT "$PKG"
    sleep 10
    continue
  }

  RES=$(awk '
    NR==1{next}
    $1~/^[0-9]+$/ && $2~/^[0-9]+$/ && $3~/^[0-9]+$/ && $2>0{
      if(prev>0 && $2>prev){
        d=($2-prev)/1000000.0
        if(d>=4&&d<=250){a[++n]=d;sum+=d}
      }
      prev=$2
    }
    END{
      if(n<3)exit
      for(i=2;i<=n;i++){v=a[i];j=i-1;while(j>=1&&a[j]>v){a[j+1]=a[j];j--}a[j+1]=v}
      avg=sum/n
      med=a[int((n-1)*.50)+1]
      p95=a[int((n-1)*.95)+1]
      p99=a[int((n-1)*.99)+1]
      thr=med*1.75
      if(med+8>thr)thr=med+8
      jank=0
      for(i=1;i<=n;i++)if(a[i]>thr)jank++
      printf "%.2f %.1f %.1f %.2f %.2f %d %.2f",avg,1000/avg,(jank*100)/n,p95,p99,n,thr
    }' "$RAW" 2>/dev/null)
  rm -f "$RAW"

  if [ -z "$RES" ]; then
    rm -f "$CACHE"
    publish_unavailable PARSER_NO_FRAMES "$PKG"
    sleep 10
    continue
  fi

  FRAME_MS=$(echo "$RES"|awk '{print $1}')
  FPS=$(echo "$RES"|awk '{print $2}')
  JANK=$(echo "$RES"|awk '{print $3}')
  P95=$(echo "$RES"|awk '{print $4}')
  P99=$(echo "$RES"|awk '{print $5}')
  N=$(echo "$RES"|awk '{print $6}')
  THR=$(echo "$RES"|awk '{print $7}')

  T="$OUT.tmp.$$"
  {
    echo "FRAME_EVIDENCE=VALID"
    echo "FRAME_REASON=OK"
    echo "FRAME_PACKAGE=$PKG"
    echo "FRAME_AT=$(date +%s)"
    echo "FRAME_MS=$FRAME_MS"
    echo "FPS_EST=$FPS"
    echo "JANK_PCT=$JANK"
    echo "P95_MS=$P95"
    echo "P99_MS=$P99"
    echo "FRAME_N=$N"
    echo "JANK_THRESHOLD_MS=$THR"
  } > "$T"
  chmod 644 "$T"; mv -f "$T" "$OUT"
  sleep 10
done
