#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
b=root/'app/build.gradle.kts'
manifest=root/'app/src/main/AndroidManifest.xml'

s=m.read_text()
# Product identity.
s=re.sub(r'CONTROL CENTER • v0\.12\.1-r10\.2 • LOCAL REALTIME 1s','MONITOR • v0.12.1-r11 • R78 READ-ONLY • REALTIME 1s',s,count=1)
s=re.sub(r'CONTROL CENTER • v0\.12\.1-r2 • DJAEGER-AI v12\.9\.50-r3 SYNC • REALTIME 1s','MONITOR • v0.12.1-r11 • R78 READ-ONLY • REALTIME 1s',s,count=1)

# Replace AI tab with a pure monitoring view. Keep source file compact by replacing whole composable region.
a=s.index('@Composable fun AI(s:RuntimeState)')
bound=s.find('@Composable fun History',a)
if bound<0: raise SystemExit('R11_FAIL=history-anchor')
monitor='''@Composable fun AI(s:RuntimeState){\n    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){\n        BoxCard("AI / CONTROL SOURCE",if(s.brain.isBlank()) "Local AI state unavailable" else s.brain,true)\n        BoxCard("STRATEGY / ENVELOPE",s.envelope.ifBlank{"No published strategy/envelope"},true)\n        BoxCard("LATEST DECISION",s.latestDecision?.let{"Profile: ${it.profile}\\nOutcome: ${it.outcome}"}?:"No structured decision published")\n        BoxCard("MONITOR-ONLY BOUNDARY","Read-only view. No mode switch, Gemini trigger, API-key action, service control, hardware tuning, game launcher, HUD, overlay or MIUI freeform action exists in this build.")\n    }\n}\n\n'''
s=s[:a]+monitor+s[bound:]

# Remove obvious UI imports left solely by old editable/key controls if compiler reports unused they are harmless.
m.write_text(s)

# Repository: make former mutation entry points unreachable from app source by deleting their functions.
rs=r.read_text()
for name in ['setUserMode','saveGeminiKey','deleteGeminiKey','geminiChat','geminiChatClear','authoritySyncStatus','kernelCapabilitySummary','maturityAudit','recoveryStatus','snapshotLifecycleStatus']:
    # Functions in this repository are single-expression or brace bodies; remove conservatively only when located.
    pat=re.compile(r'\n\s*suspend fun '+name+r'\([^\n]*?(?=\n\s*suspend fun |\n\s*private fun |\n})',re.S)
    rs,n=pat.subn('\n',rs,count=1)
    if n==0:
        print('R11_NOTE=repository function not removed:',name)
r.write_text(rs)

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12113',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r11-monitor-only"',bs,count=1)
b.write_text(bs)

# Strip overlay permission if present; r11 is a normal standalone activity.
ms=manifest.read_text()
ms=re.sub(r'\s*<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW"\s*/>','',ms)
manifest.write_text(ms)

print('R11_PRODUCT=STANDALONE_MONITOR_ONLY')
print('R11_HUD=REMOVED_FROM_PRODUCT')
print('R11_LAUNCHER=NO_GAME_LAUNCHER')
print('R11_FREEFORM=NO_MIUI_FREEFORM_ACTION')
