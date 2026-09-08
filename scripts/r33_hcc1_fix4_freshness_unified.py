#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

# FIX4 RC1: one freshness contract for every UI surface.
# Active session remains strict: telemetry sample must be fresh.
# Idle heartbeat follows the module cadence: 15-second runtime TTL.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12237',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix4-baseline-rc1"',bs,count=1)
b.write_text(bs)

ms=m.read_text()

# Centralized source of truth for STALE/FRESH semantics.
helper_anchor='private fun jankText(value:Double)=if(value.isFinite()&&value>=0.0)"%.1f%%".format(value) else "—"\n'
assert helper_anchor in ms, 'R33_FAIL=freshness-helper-anchor'
helper='''private fun runtimeStateStale(s:RuntimeState):Boolean{\n    val ttl=if(s.active=="1")5L else 15L\n    val runtimeStale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>ttl\n    return if(s.active=="1") !s.sampleFresh else runtimeStale\n}\n'''
if 'private fun runtimeStateStale(' not in ms:
    ms=ms.replace(helper_anchor,helper_anchor+helper,1)

old_status='@Composable fun StatusCard(s:RuntimeState){val runtimeTtl=if(s.active=="1")5 else 15;val runtimeStale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>runtimeTtl;val stale=if(s.active=="1") !s.sampleFresh else runtimeStale;'
new_status='@Composable fun StatusCard(s:RuntimeState){val stale=runtimeStateStale(s);'
assert old_status in ms, 'R33_FAIL=status-freshness-anchor'
ms=ms.replace(old_status,new_status,1)

old_strategy='(if((s.active=="1" && !s.sampleFresh)||(s.active!="1" && (s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5))) "STALE SNAPSHOT — NOT CURRENT RUNTIME\\n" else "")'
new_strategy='(if(runtimeStateStale(s)) "STALE SNAPSHOT — NOT CURRENT RUNTIME\\n" else "")'
assert old_strategy in ms, 'R33_FAIL=strategy-freshness-anchor'
ms=ms.replace(old_strategy,new_strategy,1)

old_diag='if(s.updated>0&&now-s.updated>5)a.add("Runtime status stale (${now-s.updated}s)")'
new_diag='if(runtimeStateStale(s))a.add(if(s.updated>0)"Runtime status stale (${now-s.updated}s)" else "Runtime status stale / not reported")'
assert old_diag in ms, 'R33_FAIL=diagnostics-freshness-anchor'
ms=ms.replace(old_diag,new_diag,1)

old_safety='@Composable fun Safety(s:RuntimeState){val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;'
new_safety='@Composable fun Safety(s:RuntimeState){val stale=runtimeStateStale(s);'
assert old_safety in ms, 'R33_FAIL=safety-freshness-anchor'
ms=ms.replace(old_safety,new_safety,1)

old_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix4-baseline • HERMES COGNITION VNEXT • HCC1'
new_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix4-baseline-rc1 • HERMES COGNITION VNEXT • HCC1'
assert old_header in ms, 'R33_FAIL=header-anchor'
ms=ms.replace(old_header,new_header,1)

m.write_text(ms)

# Independent static gates.
M=m.read_text(); B=b.read_text()
assert 'versionCode = 12237' in B
assert 'fix4-baseline-rc1' in B
assert M.count('private fun runtimeStateStale(')==1
for token in [
    '@Composable fun StatusCard(s:RuntimeState){val stale=runtimeStateStale(s);',
    'if(runtimeStateStale(s)) "STALE SNAPSHOT — NOT CURRENT RUNTIME',
    'if(runtimeStateStale(s))a.add(',
    '@Composable fun Safety(s:RuntimeState){val stale=runtimeStateStale(s);',
]:
    assert token in M, token
for forbidden in [
    's.updated>0&&now-s.updated>5',
    's.active!="1" && (s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5)',
    '@Composable fun Safety(s:RuntimeState){val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;',
]:
    assert forbidden not in M, forbidden
# Keep the previously proven FIX4 contracts intact.
assert 'jankText(s.telemetry.jank)' in M
assert 'HumanComfortHcc1Card(s);' in M
assert 'TELEMETRI 1 DETIK' in M
print('FIX4_RC1_FRESHNESS_SINGLE_FUNCTION=PASS')
print('FIX4_RC1_ACTIVE_FRESHNESS=TELEMETRY_STRICT')
print('FIX4_RC1_IDLE_RUNTIME_TTL_SEC=15')
print('FIX4_RC1_STATUS_STRATEGY_DIAGNOSTICS_SAFETY_SYNC=PASS')
print('FIX4_RC1_JANK_HCC1_SINGLE_SNAPSHOT=PRESERVED')
