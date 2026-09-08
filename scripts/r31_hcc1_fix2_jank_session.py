#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12235',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix2"',bs,count=1)
b.write_text(bs)

rs=r.read_text()
# Distinguish a real measured zero-jank result from unavailable data.
assert 'val jank:Double=0.0' in rs, 'FIX2_FAIL=telemetry-jank-default-anchor'
rs=rs.replace('val jank:Double=0.0','val jank:Double=-1.0',1)
assert 'field(11).toDoubleOrNull()?:0.0' in rs, 'FIX2_FAIL=parse-jank-anchor'
rs=rs.replace('field(11).toDoubleOrNull()?:0.0','field(11).toDoubleOrNull()?:-1.0',1)

# Runtime heartbeat semantics: active cadence is ~1 s, idle publication can be ~10 s.
# The old universal 5 s TTL made an otherwise healthy idle snapshot appear STALE for
# roughly half of every idle cycle. Active state remains strict at 5 s.
old_block='''        val runtimeUpdated=(rt["UPDATED_AT"] ?: rt["updated_at"])?.toLongOrNull() ?: 0L\n        val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..5\n        val activeClaim=(rt["ACTIVE"] ?: rt["active"] ?: "0") == "1"\n        val volatileFresh=runtimeFresh || (activeClaim && fresh)\n'''
assert old_block in rs, 'FIX2_FAIL=runtime-freshness-anchor'
new_block='''        val runtimeUpdated=(rt["UPDATED_AT"] ?: rt["updated_at"])?.toLongOrNull() ?: 0L\n        val activeClaim=(rt["ACTIVE"] ?: rt["active"] ?: "0") == "1"\n        val runtimeTtlSec=if(activeClaim) 5L else 15L\n        val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..runtimeTtlSec\n        val volatileFresh=runtimeFresh || (activeClaim && fresh)\n'''
rs=rs.replace(old_block,new_block,1)
r.write_text(rs)

ms=m.read_text()
old_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync • HERMES COGNITION VNEXT • HCC1'
new_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix2 • HERMES COGNITION VNEXT • HCC1'
assert old_header in ms, 'FIX2_FAIL=header-anchor'
ms=ms.replace(old_header,new_header,1)

# 0.0% jank is a valid measurement, not missing data.
helper_anchor='private fun positiveText(value:Double,suffix:String)='
idx=ms.index(helper_anchor)
line_end=ms.index('\n',idx)+1
helper='private fun jankText(value:Double)=if(value.isFinite()&&value>=0.0)"%.1f%%".format(value) else "—"\n'
if 'private fun jankText(' not in ms:
    ms=ms[:line_end]+helper+ms[line_end:]

ov_start=ms.index('@Composable fun Overview(s:RuntimeState)')
ov_end=ms.index('@Composable fun StatusCard',ov_start)
ov=ms[ov_start:ov_end]
j_start=ov.index('Metric("Jank",')
j_tail=ov.index(',Modifier.weight(1f))',j_start)
ov=ov[:j_start]+'Metric("Jank",jankText(s.telemetry.jank)'+ov[j_tail:]
ms=ms[:ov_start]+ov+ms[ov_end:]

# Match UI stale indicator to the same active/idle runtime heartbeat contract.
status_start=ms.index('@Composable fun StatusCard(s:RuntimeState)')
status_end=ms.index('@Composable fun ThermalRow',status_start)
status=ms[status_start:status_end]
old_stale='val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;'
assert old_stale in status, 'FIX2_FAIL=status-stale-anchor'
new_stale='val runtimeTtl=if(s.active=="1")5 else 15;val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>runtimeTtl;'
status=status.replace(old_stale,new_stale,1)
ms=ms[:status_start]+status+ms[status_end:]
m.write_text(ms)

# Final static guarantees.
R=r.read_text(); M=m.read_text(); B=b.read_text()
assert 'versionCode = 12235' in B
assert 'val jank:Double=-1.0' in R
assert 'field(11).toDoubleOrNull()?:-1.0' in R
assert 'runtimeTtlSec=if(activeClaim) 5L else 15L' in R
assert 'jankText(s.telemetry.jank)' in M
assert 'value>=0.0' in M
assert 'val runtimeTtl=if(s.active=="1")5 else 15' in M
# HCC1 and one-atomic-snapshot contracts remain intact.
for token in ['hermesHumanComfort=mapped.hermesHumanComfort','djaeger-ai comfort $arg','djaeger-ai feedback $arg','ConsolidatedSnapshotReader']:
    assert token in R, token
snap=R[R.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){'):R.index('    suspend fun setUserMode',R.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){'))]
for forbidden in ['/sys/','ProcessBuilder','djaeger-ai comfort','djaeger-ai feedback']:
    assert forbidden not in snap, forbidden
print('HCC1_FIX2_JANK_ZERO_IS_VALID=PASS')
print('HCC1_FIX2_JANK_UNAVAILABLE_SENTINEL=-1.0')
print('HCC1_FIX2_RUNTIME_TTL_ACTIVE_SEC=5')
print('HCC1_FIX2_RUNTIME_TTL_IDLE_SEC=15')
print('HCC1_FIX2_SINGLE_ATOMIC_SNAPSHOT=PRESERVED')
print('HCC1_FIX2_HCC1_CONTRACT=PRESERVED')
