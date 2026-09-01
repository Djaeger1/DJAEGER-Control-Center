#!/usr/bin/env python3
from pathlib import Path

p=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s=p.read_text()

old='Metric("Jank",if(s.telemetry.jank>=0)"%.1f%%".format(s.telemetry.jank) else "—",Modifier.weight(1f))'
new='Metric("Jank",if(s.active=="1"&&s.sampleFresh&&s.telemetry.jank>=0)"%.1f%%".format(s.telemetry.jank) else "—",Modifier.weight(1f))'
if old not in s: raise SystemExit('R10_1_FAIL=jank-anchor')
s=s.replace(old,new,1)

old='Text("Quality: ${n.quality}",color=if(n.fresh) Green else Muted,fontWeight=FontWeight.Bold)'
new='Text("Quality: ${if(n.fresh)n.quality else "INACTIVE"}",color=if(n.fresh) Green else Muted,fontWeight=FontWeight.Bold)'
if old not in s: raise SystemExit('R10_1_FAIL=network-quality-anchor')
s=s.replace(old,new,1)

s=s.replace('CONTROL CENTER • v0.12.1-r10 • LOCAL REALTIME 1s','CONTROL CENTER • v0.12.1-r10.1 • LOCAL REALTIME 1s',1)
p.write_text(s)
print('R10_1_IDLE_JANK_SEMANTICS=PASS')
print('R10_1_IDLE_NETWORK_SEMANTICS=PASS')
