#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

# Baseline hardening on top of HCC1 FULLSYNC FIX2.
# Remove the independent 5 Hz root reader for fast_telemetry. The existing
# 1-second atomic cc_snapshot already carries the authoritative telemetry row,
# runtime/session identity, frame/jank, Hermes, HCC1, CTX1 and COG1 truth.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12236',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix4-baseline"',bs,count=1)
b.write_text(bs)

rs=r.read_text()
start=rs.index('    data class FastTelemetry(')
end=rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){',start)
removed=rs[start:end]
assert 'while true; do cat /data/adb/djaeger_ai/fast_telemetry' in removed
assert 'ProcessBuilder("su", "-c", cmd)' in removed
rs=rs[:start]+rs[end:]
# The only automatic recurring read in the repository is now the atomic snapshot.
snap=rs[rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){'):rs.index('    suspend fun setUserMode',rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){'))]
assert 'ConsolidatedSnapshotReader' in snap
assert 'fast_telemetry' not in rs
assert 'ensureFastStream' not in rs
assert 'suspend fun fastTelemetry' not in rs
r.write_text(rs)

ms=m.read_text()
old_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix2 • HERMES COGNITION VNEXT • HCC1'
new_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix4-baseline • HERMES COGNITION VNEXT • HCC1'
assert old_header in ms
ms=ms.replace(old_header,new_header,1)
old='''        var fastTelemetryState by remember { mutableStateOf(DjaegerRepository.FastTelemetry()) }
        LaunchedEffect(Unit) { while (true) { fastTelemetryState = repo.fastTelemetry(); kotlinx.coroutines.delay(1) } }
        Text("FAST TELEMETRY • LITTLE ${fastTelemetryState.littleKhz/1000} MHz • BIG ${fastTelemetryState.bigKhz/1000} MHz • GPU ${fastTelemetryState.gpuHz/1000000} MHz")'''
assert old in ms
new='''        Text("TELEMETRI 1 DETIK • LITTLE ${if(s.telemetry.littleKhz>=0)s.telemetry.littleKhz/1000 else 0} MHz • BIG ${if(s.telemetry.bigKhz>=0)s.telemetry.bigKhz/1000 else 0} MHz • GPU ${if(s.telemetry.gpuHz>=0)s.telemetry.gpuHz/1000000 else 0} MHz")'''
ms=ms.replace(old,new,1)
# Preserve HCC1 and exact Overview order.
assert 'HumanComfortHcc1Card(s);' in ms
ov_start=ms.index('@Composable fun Overview(s:RuntimeState)'); ov_end=ms.index('@Composable fun StatusCard',ov_start); ov=ms[ov_start:ov_end]
req=['ThoughtsCard(s);','Metric("FPS"','Metric("Frame"','Metric("Jank"','ThermalRow(s);','NetworkCard(s.network);','HermesCard(s);','HumanComfortHcc1Card(s);','ContextVNextCard(s);']
pos=[ov.index(x) for x in req]; assert pos==sorted(pos)
assert 'fastTelemetryState' not in ms and 'repo.fastTelemetry()' not in ms
m.write_text(ms)

# Final baseline gates.
R=r.read_text(); M=m.read_text(); B=b.read_text()
assert 'versionCode = 12236' in B
assert 'fix4-baseline' in B
assert 'ConsolidatedSnapshotReader' in R
assert 'while true; do cat /data/adb/djaeger_ai/fast_telemetry' not in R
assert 'ProcessBuilder("su", "-c", cmd)' not in R
assert 'TELEMETRI 1 DETIK' in M
assert 'jankText(s.telemetry.jank)' in M
assert 'hermesHumanComfort=mapped.hermesHumanComfort' in R
print('FIX4_APK_BASELINE=HCC1_FULLSYNC_FIX2')
print('FIX4_GLOBAL_FAST_ROOT_PROCESS=REMOVED')
print('FIX4_RECURRING_TRUTH=ATOMIC_CC_SNAPSHOT_1S')
print('FIX4_JANK_ZERO_VALID=PRESERVED')
print('FIX4_HCC1_FULLSYNC=PRESERVED')
print('FIX4_OVERVIEW_ORDER=PRESERVED')
