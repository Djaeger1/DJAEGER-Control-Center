#!/system/bin/sh
# RUNTIMEFIX1: choose a SurfaceFlinger layer by real advancing presentation
# timestamps, not merely by the first layer name containing the package.
ROOT="$1"
SNAP="$ROOT/runtime/snapshot.env"
OUT="$ROOT/runtime/frame.env"
CACHE="$ROOT/runtime/frame_layer.env"
WORKLOAD="$ROOT/runtime/workload.env"

capture(){
  if command -v timeout >/dev/null 2>&1; then timeout 2 "$@"; else "$@"; fi
}

publish_unavailable(){
  t="$OUT.tmp.$$"
  {
    echo "FRAME_EVIDENCE=UNAVAILABLE"
    echo "FRAME_REASON=$1"
    echo "FRAME_PACKAGE=$2"
    echo "FRAME_AT=$(date +%s)"
    echo "FRAME_MS=NA"
    echo "FPS_EST=NA"
    echo "JANK_PCT=NA"
    echo "P95_MS=NA"
    echo "P99_MS=NA"
    echo "FRAME_N=0"
  } > "$t"
  chmod 644 "$t"; mv -f "$t" "$OUT"
}

parse_latency(){
  awk '
    NR==1{next}
    $1~/^[0-9]+$/ && $2~/^[0-9]+$/ && $3~/^[0-9]+$/ && $2>0{
      if(prev>0 && $2>prev){
        d=($2-prev)/1000000.0
        if(d>=4&&d<=250){a[++n]=d}
      }
      prev=$2
    }
    END{
      if(n<3)exit
      start=n-29; if(start<1)start=1
      m=0; sum=0
      for(i=start;i<=n;i++){b[++m]=a[i];sum+=a[i]}
      for(i=2;i<=m;i++){v=b[i];j=i-1;while(j>=1&&b[j]>v){b[j+1]=b[j];j--}b[j+1]=v}
      avg=sum/m
      med=b[int((m-1)*.50)+1]
      p95=b[int((m-1)*.95)+1]
      p99=b[int((m-1)*.99)+1]
      thr=med*1.75
      if(med+8>thr)thr=med+8
      jank=0
      for(i=1;i<=m;i++)if(b[i]>thr)jank++
      printf "%.2f %.1f %.1f %.2f %.2f %d %.2f",avg,1000/avg,(jank*100)/m,p95,p99,m,thr
    }' "$1" 2>/dev/null
}

try_layer(){
  CAND="$1"
  [ -n "$CAND" ] || return 1
  RAW="$ROOT/runtime/.sf_latency.$$"
  capture dumpsys SurfaceFlinger --latency "$CAND" > "$RAW" 2>/dev/null || { rm -f "$RAW"; return 1; }
  TRY_RES=$(parse_latency "$RAW")
  rm -f "$RAW"
  [ -n "$TRY_RES" ] || return 1
  SELECTED_LAYER="$CAND"
  SELECTED_RES="$TRY_RES"
  return 0
}

while true; do
  [ -r "$SNAP" ] || { sleep 5; continue; }
  PKG=$(sed -n 's/^ACTIVE_PACKAGE=//p' "$SNAP" | head -n1)
  WPKG=$(sed -n 's/^PACKAGE=//p' "$WORKLOAD" 2>/dev/null | head -n1)
  WCLASS=$(sed -n 's/^WORKLOAD_CLASS=//p' "$WORKLOAD" 2>/dev/null | head -n1)
  if [ "$WPKG" != "$PKG" ] || { [ "$WCLASS" != GAME ] && [ "$WCLASS" != APP ]; }; then
    [ -n "$PKG" ] || PKG=UNKNOWN
    publish_unavailable WORKLOAD_NOT_FRAME_ELIGIBLE "$PKG"
    sleep 10
    continue
  fi

  SELECTED_LAYER=""
  SELECTED_RES=""
  CACHED=""
  if [ -r "$CACHE" ] && [ "$(sed -n 's/^PACKAGE=//p' "$CACHE" | head -n1)" = "$PKG" ]; then
    CACHED=$(sed -n 's/^LAYER=//p' "$CACHE" | head -n1)
  fi
  if [ -n "$CACHED" ]; then
    try_layer "$CACHED" || rm -f "$CACHE"
  fi

  if [ -z "$SELECTED_RES" ]; then
    LIST="$ROOT/runtime/.sf_list.$$"
    CANDS="$ROOT/runtime/.sf_candidates.$$"
    capture dumpsys SurfaceFlinger --list > "$LIST" 2>/dev/null || {
      rm -f "$LIST" "$CANDS"
      publish_unavailable SURFACEFLINGER_LIST_TIMEOUT "$PKG"
      sleep 8
      continue
    }
    {
      grep -F "$PKG" "$LIST" 2>/dev/null | grep -F "SurfaceView[" | grep -F "(BLAST)" || true
      grep -F "$PKG" "$LIST" 2>/dev/null | grep -F "(BLAST)" || true
      grep -F "$PKG" "$LIST" 2>/dev/null || true
    } | awk 'NF&&!seen[$0]++' | head -n 24 > "$CANDS"
    rm -f "$LIST"

    FOUND_CANDIDATE=NO
    while IFS= read -r CAND; do
      [ -n "$CAND" ] || continue
      FOUND_CANDIDATE=YES
      if try_layer "$CAND"; then break; fi
    done < "$CANDS"
    rm -f "$CANDS"

    if [ -z "$SELECTED_RES" ]; then
      rm -f "$CACHE"
      if [ "$FOUND_CANDIDATE" = YES ]; then REASON=NO_PRESENTATION_LAYER; else REASON=LAYER_NOT_FOUND; fi
      publish_unavailable "$REASON" "$PKG"
      sleep 8
      continue
    fi
  fi

  # VALID_PRESENTATION_LAYER: cache only after advancing presentation timestamps.
  {
    echo "PACKAGE=$PKG"
    echo "LAYER=$SELECTED_LAYER"
  } > "$CACHE.tmp.$$"
  chmod 600 "$CACHE.tmp.$$"; mv -f "$CACHE.tmp.$$" "$CACHE"

  FRAME_MS=$(echo "$SELECTED_RES"|awk '{print $1}')
  FPS=$(echo "$SELECTED_RES"|awk '{print $2}')
  JANK=$(echo "$SELECTED_RES"|awk '{print $3}')
  P95=$(echo "$SELECTED_RES"|awk '{print $4}')
  P99=$(echo "$SELECTED_RES"|awk '{print $5}')
  N=$(echo "$SELECTED_RES"|awk '{print $6}')
  THR=$(echo "$SELECTED_RES"|awk '{print $7}')

  T="$OUT.tmp.$$"
  {
    echo "FRAME_EVIDENCE=VALID"
    echo "FRAME_REASON=VALID_PRESENTATION_LAYER"
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
  sleep 5
done
