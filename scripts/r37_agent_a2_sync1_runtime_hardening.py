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

# Top header must reflect the actual matched pair rather than an older generated stage.
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

# Session sample isolation. Scope changes strictly to App() so no other code path is rewritten.
app_start=ms.index('@Composable fun App()')
app_end=ms.index('@Composable fun Overview',app_start)
app=ms[app_start:app_end]

# Add a rolling-sample session identity state beside the existing samples state.
if 'sampleSessionKey' not in app:
    app2,n=re.subn(
        r'(val\s+samples\s*=\s*remember\s*\{\s*mutableStateListOf<Sample>\(\)\s*\})',
        r'\1;var sampleSessionKey by remember{mutableStateOf("")}',
        app,
        count=1,
    )
    assert n==1, 'R37_FAIL=samples-state-anchor'
    app=app2

# Replace only the recurring snapshot assignment in App(). This tolerates formatting changes
# introduced by the prior FIX4 patch chain.
if 'val next=repo.snapshot()' not in app:
    app2,n=re.subn(
        r'while\s*\(true\)\s*\{\s*state\s*=\s*repo\.snapshot\(\)\s*;',
        'while(true){val next=repo.snapshot();val nextKey="${next.active}|${next.game}|${next.window}|${next.controllerPid}";if(sampleSessionKey.isNotBlank()&&nextKey!=sampleSessionKey)samples.clear();sampleSessionKey=nextKey;state=next;',
        app,
        count=1,
    )
    assert n==1, 'R37_FAIL=snapshot-loop-anchor'
    app=app2
    # The snapshot sampled in this loop is now `next`; use it consistently for the sample append.
    app2,n=re.subn(
        r'if\s*\(state\.root&&state\.installed&&state\.sampleFresh\)\s*\{\s*with\(state\.telemetry\)',
        'if(next.root&&next.installed&&next.sampleFresh){with(next.telemetry)',
        app,
        count=1,
    )
    assert n==1, 'R37_FAIL=sample-append-anchor'
    app=app2

ms=ms[:app_start]+app+ms[app_end:]

# Freshness semantics were already hardened by HCC1 FIX2 and must be preserved, not replaced.
assert 'val runtimeTtl=if(s.active=="1")5 else 15' in ms, 'R37_FAIL=runtime-ttl-regressed'
assert 'val stale=if(s.active=="1") !s.sampleFresh else runtimeStale' in ms, 'R37_FAIL=active-freshness-regressed'

# Avoid misleading generic local-brain language in the dual-brain architecture.
ms=ms.replace('No active Local Brain state.','No Hermes H2 state published.')
ms=ms.replace('BoxCard("LOCAL BRAIN LIVE"','BoxCard("HERMES H2 LOCAL BRAIN LIVE"')

# Matched pair status must be visible in Overview.
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
assert 'sampleSessionKey' in M and 'samples.clear()' in M and 'val next=repo.snapshot()' in M
assert 'val runtimeTtl=if(s.active=="1")5 else 15' in M
assert 'val stale=if(s.active=="1") !s.sampleFresh else runtimeStale' in M
assert 'No active Local Brain state.' not in M
assert 'HERMES H2 LOCAL BRAIN LIVE' in M
start=M.index('@Composable fun Overview(s:RuntimeState)');end=M.index('@Composable fun StatusCard',start);O=M[start:end]
assert 'MatchedPairSyncCard(s)' in O
for stale in ['CONTROL CENTER • v0.12.1-r2','DJAEGER-AI v12.9.50-r3 SYNC','DJAEGER v0.12.1-r2 • AI SYNC']:
    assert stale not in M, stale
print('R37_IDENTITY_FIX=PASS')
print('R37_EXACT_MODULE_COMPATIBILITY=PASS')
print('R37_SESSION_SAMPLE_ISOLATION=PASS')
print('R37_ACTIVE_IDLE_FRESHNESS=PRESERVED')
print('R37_HERMES_SEMANTICS=PASS')
print('R37_MATCHED_PAIR_OVERVIEW=PASS')
