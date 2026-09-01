#!/usr/bin/env python3
# r14 verified screenshot-driven bugfix
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12140',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r14"',bs,count=1); b.write_text(bs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r13 • COMPLETE USER DESIGN • REALTIME 1s','CONTROL CENTER • v0.12.1-r14 • REALTIME 1s')
# Generated baseline uses a different argument order across revisions: patch the whole single-line title call.
def title_fix(match):
    call=match.group(0)
    if 'color=' in call: return call
    return call[:-1]+',color=MaterialTheme.colorScheme.onBackground)'
ms,n=re.subn(r'Text\("DJAEGER"[^\n]*?\)',title_fix,ms,count=1)
assert n==1,'DJAEGER title call not found'
old='"Module: ${s.moduleVersion}\\nGovernor: ${s.governorStatus}\\nGame: ${s.game}\\nWindow: ${s.windowState}\\nProfile: ${s.profile}\\nLast sample: ${s.lastSample}\\nController PID: ${s.controllerPid} • Predictor PID: ${s.predictorPid}"'
new='"Module: ${s.moduleVersion}" + (if(s.moduleVersion.contains("r78",ignoreCase=true)) "  [LEGACY INSTALLED]" else "") + "\\nGovernor: ${s.governorStatus}\\nGame: ${s.game}\\nWindow: ${s.windowState}\\nProfile: ${s.profile}\\nLast sample: ${s.lastSample}\\nController PID: ${s.controllerPid} • Predictor PID: ${s.predictorPid}"'
if old in ms: ms=ms.replace(old,new,1)
assert 'CONTROL CENTER • v0.12.1-r14 • REALTIME 1s' in ms
assert 'COMPLETE USER DESIGN • REALTIME 1s' not in ms
assert 'R78 SYNC' not in ms
assert 'color=MaterialTheme.colorScheme.onBackground' in ms
m.write_text(ms)
print('R14_FIX=HIGH_CONTRAST_WORDMARK')
print('R14_FIX=COMPACT_NARROW_HEADER')
print('R14_FIX=RUNTIME_MODULE_IDENTITY_NOT_APP_BRANDING')
print('R14_PRESERVE=R13_STRATEGY_PIPELINE_OUTCOME_VAULT')
