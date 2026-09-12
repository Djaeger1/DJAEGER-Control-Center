#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
b=root/'app/build.gradle.kts'
ms=m.read_text()
bs=b.read_text()

bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12241',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.2-agent-a2-sync1-fix1"',bs,count=1)

ms=re.sub(r'Text\("CONTROL CENTER[^\"]*",color=Muted\)','Text("CONTROL CENTER • v0.12.2 A2 SYNC1 FIX1 • REALTIME 1s",color=Muted)',ms,count=1)
ms=ms.replace('DJAEGER v0.12.1-r2 • AI SYNC\\n[','DJAEGER Control Center v0.12.2 A2 SYNC1 FIX1\\n[')
ms=ms.replace('val supported=s.moduleVersion.contains("12.9.50")','val supported=s.moduleVersion.contains("DUALBRAIN-AGENT-A2-SYNC1")')
ms=ms.replace('REQUIRES DJAEGER v12.9.21+','REQUIRES A2 SYNC1 MATCHED MODULE')

# Isolate rolling chart data by runtime session without touching any other composable.
app_start=ms.index('@Composable fun App()')
app_end=ms.index('@Composable fun Overview',app_start)
app=ms[app_start:app_end]
if 'sampleSessionKey' not in app:
    app,n=re.subn(r'(val\s+samples\s*=\s*remember\s*\{\s*mutableStateListOf<Sample>\(\)\s*\})',r'\1;var sampleSessionKey by remember{mutableStateOf("")}',app,count=1)
    assert n==1,'R37_FAIL=samples-state-anchor'
if 'val next=repo.snapshot()' not in app:
    app,n=re.subn(r'while\s*\(true\)\s*\{\s*state\s*=\s*repo\.snapshot\(\)\s*;','while(true){val next=repo.snapshot();val nextKey="${next.active}|${next.game}|${next.window}|${next.controllerPid}";if(sampleSessionKey.isNotBlank()&&nextKey!=sampleSessionKey)samples.clear();sampleSessionKey=nextKey;state=next;',app,count=1)
    assert n==1,'R37_FAIL=snapshot-loop-anchor'
    app,n=re.subn(r'if\s*\(state\.root&&state\.installed&&state\.sampleFresh\)\s*\{\s*with\(state\.telemetry\)','if(next.root&&next.installed&&next.sampleFresh){with(next.telemetry)',app,count=1)
    assert n==1,'R37_FAIL=sample-append-anchor'
ms=ms[:app_start]+app+ms[app_end:]

# RC1 already has one centralized freshness function. Preserve that exact contract.
assert 'private fun runtimeStateStale(s:RuntimeState):Boolean' in ms,'R37_FAIL=unified-freshness-missing'
assert 'val ttl=if(s.active=="1")5L else 15L' in ms,'R37_FAIL=unified-freshness-ttl'
assert 'return if(s.active=="1") !s.sampleFresh else runtimeStale' in ms,'R37_FAIL=unified-freshness-active-rule'

ms=ms.replace('No active Local Brain state.','No Hermes H2 state published.')
ms=ms.replace('BoxCard("LOCAL BRAIN LIVE"','BoxCard("HERMES H2 LOCAL BRAIN LIVE"')

overview_start=ms.index('@Composable fun Overview(s:RuntimeState)')
overview_end=ms.index('@Composable fun StatusCard',overview_start)
ov=ms[overview_start:overview_end]
if 'MatchedPairSyncCard(s)' not in ov:
    anchor='StatusCard(s);'
    assert anchor in ov,'R37_FAIL=status-card-anchor'
    absolute=overview_start+ov.index(anchor)+len(anchor)
    ms=ms[:absolute]+'MatchedPairSyncCard(s);'+ms[absolute:]

m.write_text(ms); b.write_text(bs)
M=m.read_text(); B=b.read_text()
assert 'versionCode = 12241' in B
assert 'versionName = "0.12.2-agent-a2-sync1-fix1"' in B
assert 'CONTROL CENTER • v0.12.2 A2 SYNC1 FIX1 • REALTIME 1s' in M
assert 'DJAEGER Control Center v0.12.2 A2 SYNC1 FIX1\\n[' in M
assert 'val supported=s.moduleVersion.contains("DUALBRAIN-AGENT-A2-SYNC1")' in M
assert 'sampleSessionKey' in M and 'samples.clear()' in M and 'val next=repo.snapshot()' in M
assert 'private fun runtimeStateStale(s:RuntimeState):Boolean' in M
assert 'val ttl=if(s.active=="1")5L else 15L' in M
assert 'return if(s.active=="1") !s.sampleFresh else runtimeStale' in M
assert 'No active Local Brain state.' not in M
assert 'HERMES H2 LOCAL BRAIN LIVE' in M
start=M.index('@Composable fun Overview(s:RuntimeState)'); end=M.index('@Composable fun StatusCard',start); O=M[start:end]
assert 'MatchedPairSyncCard(s)' in O
for stale in ['CONTROL CENTER • v0.12.1-r2','DJAEGER-AI v12.9.50-r3 SYNC','DJAEGER v0.12.1-r2 • AI SYNC']:
    assert stale not in M,stale
print('R37_IDENTITY_FIX=PASS')
print('R37_EXACT_MODULE_COMPATIBILITY=PASS')
print('R37_SESSION_SAMPLE_ISOLATION=PASS')
print('R37_UNIFIED_FRESHNESS=PRESERVED')
print('R37_HERMES_SEMANTICS=PASS')
print('R37_MATCHED_PAIR_OVERVIEW=PASS')
