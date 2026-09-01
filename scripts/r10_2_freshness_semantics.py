#!/usr/bin/env python3
from pathlib import Path

p=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s=p.read_text()

old='@Composable fun StatusCard(s:RuntimeState){val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;val session='
new='@Composable fun StatusCard(s:RuntimeState){val runtimeStale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;val stale=if(s.active=="1") !s.sampleFresh else runtimeStale;val session='
if old not in s: raise SystemExit('R10_2_FAIL=status-freshness-anchor')
s=s.replace(old,new,1)

s=s.replace('CONTROL CENTER • v0.12.1-r10.1 • LOCAL REALTIME 1s','CONTROL CENTER • v0.12.1-r10.2 • LOCAL REALTIME 1s',1)
p.write_text(s)
print('R10_2_ACTIVE_FRESHNESS=TELEMETRY_EPOCH')
print('R10_2_IDLE_FRESHNESS=RUNTIME_UPDATED_AT')
print('R10_2_STATUS_SEMANTICS=PASS')
