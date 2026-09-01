#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12140',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r14"',bs,count=1); b.write_text(bs)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r13 • COMPLETE USER DESIGN • REALTIME 1s','CONTROL CENTER • v0.12.1-r14 • REALTIME 1s')
def title_fix(match):
 call=match.group(0)
 if 'color=' in call:return call
 return call[:-1]+',color=MaterialTheme.colorScheme.onBackground)'
ms,n=re.subn(r'Text\("DJAEGER"[^\n]*?\)',title_fix,ms,count=1); assert n==1
old='"Module: ${s.moduleVersion}\\nGovernor: ${s.governorStatus}\\nGame: ${s.game}\\nWindow: ${s.windowState}\\nProfile: ${s.profile}\\nLast sample: ${s.lastSample}\\nController PID: ${s.controllerPid} • Predictor PID: ${s.predictorPid}"'
new='"Module: ${s.moduleVersion}" + (if(s.moduleVersion.contains("r78",ignoreCase=true)) "  [LEGACY INSTALLED]" else "") + "\\nGovernor: ${s.governorStatus}\\nGame: ${s.game}\\nWindow: ${s.windowState}\\nProfile: ${s.profile}\\nLast sample: ${s.lastSample}\\nController PID: ${s.controllerPid} • Predictor PID: ${s.predictorPid}"'
if old in ms:ms=ms.replace(old,new,1)
# Existing StatusCard already computes active-aware stale. Strategy card uses same authoritative freshness inputs.
old2='BoxCard("STRATEGY COMPOSITION","Source: ${x.source}\\nMode: ${s.userMode}'
new2='BoxCard("STRATEGY COMPOSITION",(if((s.active=="1" && !s.sampleFresh)||(s.active!="1" && (s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5))) "STALE SNAPSHOT — NOT CURRENT RUNTIME\\n" else "")+"Source: ${x.source}\\nMode: ${s.userMode}'
if old2 in ms:ms=ms.replace(old2,new2,1)
m.write_text(ms)
rs=r.read_text()
# Fail closed for volatile values when ACTIVE claims a game but telemetry is stale; avoids screenshot contradiction game-visible vs IDLE/stale truth.
needle='        val fresh = tel.epoch > 0 && age in 0..5\n'; assert needle in rs
rs=rs.replace(needle,needle+'        val runtimeUpdated=(rt["UPDATED_AT"] ?: rt["updated_at"])?.toLongOrNull() ?: 0L\n        val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..5\n        val activeClaim=(rt["ACTIVE"] ?: rt["active"] ?: "0") == "1"\n        val volatileFresh=if(activeClaim) fresh else runtimeFresh\n',1)
rs=rs.replace('active=rt["ACTIVE"] ?: rt["active"] ?: "0",','active=if(volatileFresh) (rt["ACTIVE"] ?: rt["active"] ?: "0") else "0",',1)
rs=rs.replace('game=rt["GAME"] ?: rt["game"] ?: "NA",','game=if(volatileFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA (STALE)",',1)
rs=rs.replace('window=rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE",','window=if(volatileFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "STALE",',1)
r.write_text(rs)
assert 'R78 SYNC' not in ms
print('R14_FIX=HEADER_CONTRAST_COMPACT')
print('R14_FIX=LEGACY_MODULE_IDENTITY')
print('R14_FIX=STALE_VOLATILE_STATE_FAIL_CLOSED')
print('R14_PRESERVE=R13_STRATEGY_PIPELINE_OUTCOME_VAULT')
