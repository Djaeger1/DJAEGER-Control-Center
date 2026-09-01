#!/usr/bin/env python3
# r14 screenshot-driven bugfix
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
# Explicitly warn that stale values are historical, not current runtime truth.
old2='BoxCard("STRATEGY COMPOSITION","Source: ${x.source}\\nMode: ${s.userMode}'
new2='BoxCard("STRATEGY COMPOSITION",(if(s.freshness=="STALE") "STALE SNAPSHOT — NOT CURRENT RUNTIME\\n" else "")+"Source: ${x.source}\\nMode: ${s.userMode}'
if old2 in ms:ms=ms.replace(old2,new2,1)
m.write_text(ms)
rs=r.read_text()
needle='        val freshness = freshnessFromAge(age)\n'; assert needle in rs
rs=rs.replace(needle,needle+'        val staleSnapshot = freshness == "STALE"\n',1)
for a,c in {
'game=rt["GAME"]?:"NA"':'game=if(staleSnapshot) "NA (STALE)" else rt["GAME"]?:"NA"',
'windowMode=rt["WINDOW_MODE"]?:"NA"':'windowMode=if(staleSnapshot) "STALE" else rt["WINDOW_MODE"]?:"NA"',
'profile=rt["PROFILE"]?:"NA"':'profile=if(staleSnapshot) "NA (STALE)" else rt["PROFILE"]?:"NA"'}.items():
 if a in rs:rs=rs.replace(a,c,1)
r.write_text(rs)
assert 'R78 SYNC' not in ms
print('R14_FIX=HEADER_CONTRAST_COMPACT')
print('R14_FIX=LEGACY_MODULE_IDENTITY')
print('R14_FIX=STALE_VOLATILE_STATE_FAIL_CLOSED')
print('R14_PRESERVE=R13_STRATEGY_PIPELINE_OUTCOME_VAULT')
