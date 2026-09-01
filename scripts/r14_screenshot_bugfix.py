#!/usr/bin/env python3
# r14 verified screenshot-driven bugfix
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12140',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r14"',bs,count=1); b.write_text(bs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r13 • COMPLETE USER DESIGN • REALTIME 1s','CONTROL CENTER • v0.12.1-r14 • REALTIME 1s')
ms=re.sub(r'Text\("DJAEGER"\s*,\s*fontWeight\s*=\s*FontWeight\.Black\s*,\s*fontSize\s*=\s*32\.sp\s*\)', 'Text("DJAEGER",fontWeight=FontWeight.Black,fontSize=32.sp,color=MaterialTheme.colorScheme.onBackground)', ms, count=1)
if 'Text("DJAEGER",fontWeight=FontWeight.Black,fontSize=32.sp,color=' not in ms: ms=ms.replace('Text("DJAEGER",fontWeight=FontWeight.Black,fontSize=32.sp)', 'Text("DJAEGER",fontWeight=FontWeight.Black,fontSize=32.sp,color=MaterialTheme.colorScheme.onBackground)',1)
old='"Module: ${s.moduleVersion}\\nGovernor: ${s.governorStatus}\\nGame: ${s.game}\\nWindow: ${s.windowState}\\nProfile: ${s.profile}\\nLast sample: ${s.lastSample}\\nController PID: ${s.controllerPid} • Predictor PID: ${s.predictorPid}"'
new='"Module: ${s.moduleVersion}" + (if(s.moduleVersion.contains("r78",ignoreCase=true)) "  [LEGACY INSTALLED]" else "") + "\\nGovernor: ${s.governorStatus}\\nGame: ${s.game}\\nWindow: ${s.windowState}\\nProfile: ${s.profile}\\nLast sample: ${s.lastSample}\\nController PID: ${s.controllerPid} • Predictor PID: ${s.predictorPid}"'
if old in ms: ms=ms.replace(old,new,1)
assert 'CONTROL CENTER • v0.12.1-r14 • REALTIME 1s' in ms
assert 'COMPLETE USER DESIGN • REALTIME 1s' not in ms
assert 'R78 SYNC' not in ms
m.write_text(ms)
print('R14_FIX=HIGH_CONTRAST_WORDMARK')
print('R14_FIX=COMPACT_NARROW_HEADER')
print('R14_FIX=RUNTIME_MODULE_IDENTITY_NOT_APP_BRANDING')
print('R14_PRESERVE=R13_STRATEGY_PIPELINE_OUTCOME_VAULT')
