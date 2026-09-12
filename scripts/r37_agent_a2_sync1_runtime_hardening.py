#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
b=root/'app/build.gradle.kts'
ms=m.read_text()
bs=b.read_text()

# FIX1 identity: eliminate stale UI version strings after generated patch chain.
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12241',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.2-agent-a2-sync1-fix1"',bs,count=1)

# Top header must reflect the actual matched pair rather than the ancient r2/r3 label.
ms=re.sub(
    r'Text\("CONTROL CENTER[^\"]*",color=Muted\)',
    'Text("CONTROL CENTER • v0.12.2 A2 SYNC1 FIX1 • REALTIME 1s",color=Muted)',
    ms,
    count=1,
)

# Copy payload identity must not claim the old Control Center build.
ms=ms.replace('DJAEGER v0.12.1-r2 • AI SYNC\\n[','DJAEGER Control Center v0.12.2 A2 SYNC1 FIX1\\n[')

# Exact matched-pair support marker. A generic 12.9.50 match allowed stale modules to look supported.
ms=ms.replace('val supported=s.moduleVersion.contains("12.9.50")','val supported=s.moduleVersion.contains("DUALBRAIN-AGENT-A2-SYNC1")')
ms=ms.replace('REQUIRES DJAEGER v12.9.21+','REQUIRES A2 SYNC1 MATCHED MODULE')

# Session sample isolation: do not mix charts from a previous game/window/session.
# Add a session identity key and clear rolling samples whenever the runtime session changes.
old='''@Composable fun App(){val repo=remember{DjaegerRepository()};var state by remember{mutableStateOf(RuntimeState())};var tab by remember{mutableIntStateOf(0)};val samples=remember{mutableStateListOf<Sample>()}
    val lifecycleOwner=LocalLifecycleOwner.current
    LaunchedEffect(lifecycleOwner){lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED){while(true){state=repo.snapshot();if(state.root&&state.installed&&state.sampleFresh){with(state.telemetry){samples.add(Sample(if(fps>0)fps else Double.NaN,if(frameMs>0)frameMs else Double.NaN,sampleTemp(cpuT),sampleTemp(gpuT),sampleTemp(skinT),sampleTemp(batT)));while(samples.size>60)samples.removeAt(0)}};delay(1000)}}}'''
if old in ms:
    new='''@Composable fun App(){val repo=remember{DjaegerRepository()};var state by remember{mutableStateOf(RuntimeState())};var tab by remember{mutableIntStateOf(0)};val samples=remember{mutableStateListOf<Sample>()};var sampleSessionKey by remember{mutableStateOf("")}
    val lifecycleOwner=LocalLifecycleOwner.current
    LaunchedEffect(lifecycleOwner){lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED){while(true){val next=repo.snapshot();val nextKey="${next.active}|${next.game}|${next.window}|${next.controllerPid}";if(sampleSessionKey.isNotBlank()&&nextKey!=sampleSessionKey)samples.clear();sampleSessionKey=nextKey;state=next;if(next.root&&next.installed&&next.sampleFresh){with(next.telemetry){samples.add(Sample(if(fps>0)fps else Double.NaN,if(frameMs>0)frameMs else Double.NaN,sampleTemp(cpuT),sampleTemp(gpuT),sampleTemp(skinT),sampleTemp(batT)));while(samples.size>60)samples.removeAt(0)}};delay(1000)}}}'''
    ms=ms.replace(old,new,1)
else:
    # Later generated patches may have formatted App differently. Refuse silent omission.
    raise AssertionError('R37_FAIL=app-loop-anchor')

# Correct runtime freshness semantics: active session strict 5s, idle session 15s.
ms=ms.replace('val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;val session=',
              'val ttl=if(s.active=="1")5L else 15L;val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>ttl;val session=',1)
# Safety may contain the same fixed-5s logic; replace one further occurrence if present.
ms=ms.replace('val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;Column(',
              'val ttl=if(s.active=="1")5L else 15L;val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>ttl;Column(',1)

# Avoid misleading "Local Brain" generic label in the dual-brain architecture.
ms=ms.replace('No active Local Brain state.','No Hermes H2 state published.')
ms=ms.replace('BoxCard("LOCAL BRAIN LIVE"','BoxCard("HERMES H2 LOCAL BRAIN LIVE"')

# Matched pair card should be visible in Overview. If r36 placed it elsewhere, add it once after StatusCard.
overview_start=ms.index('@Composable fun Overview(s:RuntimeState)')
overview_end=ms.index('@Composable fun StatusCard',overview_start)
ov=ms[overview_start:overview_end]
if 'MatchedPairSyncCard(s)' not in ov:
    anchor='StatusCard(s);'
    assert anchor in ov, 'R37_FAIL=status-card-anchor'
    absolute=overview_start+ov.index(anchor)+len(anchor)
    ms=ms[:absolute]+'MatchedPairSyncCard(s);'+ms[absolute:]

m.write_text(ms)
b.write_text(bs)

M=m.read_text(); B=b.read_text()
assert 'versionCode = 12241' in B
assert 'versionName = "0.12.2-agent-a2-sync1-fix1"' in B
assert 'CONTROL CENTER • v0.12.2 A2 SYNC1 FIX1 • REALTIME 1s' in M
assert 'DJAEGER Control Center v0.12.2 A2 SYNC1 FIX1\\n[' in M
assert 'val supported=s.moduleVersion.contains("DUALBRAIN-AGENT-A2-SYNC1")' in M
assert 'sampleSessionKey' in M and 'samples.clear()' in M
assert 'val ttl=if(s.active=="1")5L else 15L' in M
assert 'No active Local Brain state.' not in M
assert 'HERMES H2 LOCAL BRAIN LIVE' in M
start=M.index('@Composable fun Overview(s:RuntimeState)');end=M.index('@Composable fun StatusCard',start);O=M[start:end]
assert 'MatchedPairSyncCard(s)' in O
for stale in ['CONTROL CENTER • v0.12.1-r2','DJAEGER-AI v12.9.50-r3 SYNC','DJAEGER v0.12.1-r2 • AI SYNC']:
    assert stale not in M, stale
print('R37_IDENTITY_FIX=PASS')
print('R37_EXACT_MODULE_COMPATIBILITY=PASS')
print('R37_SESSION_SAMPLE_ISOLATION=PASS')
print('R37_ACTIVE_IDLE_FRESHNESS=PASS')
print('R37_HERMES_SEMANTICS=PASS')
print('R37_MATCHED_PAIR_OVERVIEW=PASS')
