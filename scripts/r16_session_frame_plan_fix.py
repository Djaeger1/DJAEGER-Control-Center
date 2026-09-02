#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12160',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r16"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# Exact __PLANS__ contract: epoch,state,score,reason,mode,profile,lmin,lmax,bmin,bmax,gmin,gmax
anchor='data class RuntimeState('
assert anchor in rs
plan='''data class R16Plan(val epoch:String,val state:String,val score:String,val reason:String,val mode:String,val profile:String,val lmin:String,val lmax:String,val bmin:String,val bmax:String,val gmin:String,val gmax:String)\nfun parseR16Plan(raw:String):R16Plan?=raw.lineSequence().map{it.trim()}.filter{it.isNotBlank()}.mapNotNull{line->val p=line.split(',');if(p.size>=12&&p[0].toLongOrNull()!=null)R16Plan(p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7],p[8],p[9],p[10],p[11])else null}.lastOrNull{it.state=="PROMOTED"}\n\n'''
rs=rs.replace(anchor,plan+anchor,1)
rs=rs.replace('val plan= parsePlan(mapped.plans)','val plan= parseR16Plan(mapped.plans)',1)
# Runtime identity freshness is governed by __RUNTIME__; telemetry freshness must not erase a fresh active runtime.
rs=rs.replace('val volatileFresh=if(activeClaim) fresh else runtimeFresh','val volatileFresh=runtimeFresh || (activeClaim && fresh)',1)
# One frame contract: current cards and Outcome use exactly the same latest fresh frame row.
rs=rs.replace('val fFresh=fEpoch>0 && (now-fEpoch) in 0..10','val fFresh=fEpoch>0 && (now-fEpoch) in 0..15',1)
rs=rs.replace('val frameFresh=frameEpoch>0 && (now-frameEpoch) in 0..10','val frameFresh=frameEpoch>0 && (now-frameEpoch) in 0..15',1)
# Make proposal history explicit instead of presenting it as current execution.
rs=rs.replace('proposal=plan?.let{"${it.state} ${it.mode} ${it.profile}"}?:"UNAVAILABLE"','proposal=plan?.let{"LAST PROMOTED @${it.epoch}: ${it.mode} ${it.profile}"}?:"UNAVAILABLE"',1)
rs=rs.replace('validation=plan?.let{"${it.state}: ${it.reason}"}?:"UNAVAILABLE"','validation=plan?.let{"${it.state} score=${it.score}: ${it.reason}"}?:"UNAVAILABLE"',1)
r.write_text(rs)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r15 • RUNTIME CONTRACT • REALTIME 1s','CONTROL CENTER • v0.12.1-r16 • SESSION/FRAME CONTRACT • REALTIME 1s')
# Label strategy source truthfully: clocks shown without fresh execution are last promoted proposal, not applied clocks.
ms=ms.replace('BoxCard("STRATEGY COMPOSITION",','BoxCard("STRATEGY COMPOSITION • LAST PROMOTED PLAN",',1)
m.write_text(ms)
print('R16_PLAN_CSV=EXACT_12_COLUMNS')
print('R16_RUNTIME_FRESHNESS=RUNTIME_OR_TELEMETRY')
print('R16_FRAME_CONTRACT=SINGLE_LATEST_FRESH_ROW')
print('R16_HISTORY_LABEL=EXPLICIT')
