#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12233',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-cog1-overvieworder"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
old_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1 • HERMES COGNITION VNEXT'
new_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-overvieworder • HERMES COGNITION VNEXT'
assert old_header in ms, 'R29_FAIL=header-anchor'
ms=ms.replace(old_header,new_header,1)

# User-requested UI-only move: FPS/Frame/Jank + CPU/GPU/Skin/Battery + NETWORK
# must become one block immediately below THOUGHT and immediately above HERMES H2.
start=ms.index('@Composable fun Overview(s:RuntimeState)')
end=ms.index('@Composable fun StatusCard',start)
ov=ms[start:end]

fps_anchor='Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Metric("FPS"'
block_start=ov.index(fps_anchor)
block_tail='};ThermalRow(s);NetworkCard(s.network);'
block_end=ov.index(block_tail,block_start)+len(block_tail)
telemetry_block=ov[block_start:block_end]

# Prove this is the intended display group before moving it.
for required in ['Metric("FPS"','Metric("Frame"','Metric("Jank"','ThermalRow(s);','NetworkCard(s.network);']:
    assert required in telemetry_block, 'R29_FAIL=missing-'+required

ov=ov[:block_start]+ov[block_end:]
anchor='ThoughtsCard(s);HermesCard(s);'
assert anchor in ov, 'R29_FAIL=thought-hermes-anchor'
ov=ov.replace(anchor,'ThoughtsCard(s);'+telemetry_block+'HermesCard(s);',1)
ms=ms[:start]+ov+ms[end:]

# Exact position/order gates inside Overview only.
start=ms.index('@Composable fun Overview(s:RuntimeState)')
end=ms.index('@Composable fun StatusCard',start)
ov=ms[start:end]
assert ov.count('Metric("FPS"') == 1, 'R29_FAIL=fps-duplicate'
assert ov.count('Metric("Frame"') == 1, 'R29_FAIL=frame-duplicate'
assert ov.count('Metric("Jank"') == 1, 'R29_FAIL=jank-duplicate'
assert ov.count('ThermalRow(s);') == 1, 'R29_FAIL=thermal-duplicate'
assert ov.count('NetworkCard(s.network);') == 1, 'R29_FAIL=network-duplicate'
thought=ov.index('ThoughtsCard(s);')
fps=ov.index('Metric("FPS"')
frame=ov.index('Metric("Frame"')
jank=ov.index('Metric("Jank"')
thermal=ov.index('ThermalRow(s);')
network=ov.index('NetworkCard(s.network);')
hermes=ov.index('HermesCard(s);')
assert thought < fps < frame < jank < thermal < network < hermes, 'R29_FAIL=requested-order'

# Display move only: component implementations and backend remain unchanged.
for forbidden in ['iptables','ip6tables','settings put','setprop','force-stop','/sys/','ProcessBuilder']:
    assert forbidden not in telemetry_block, 'R29_FAIL=unexpected-'+forbidden

m.write_text(ms)
print('R29_OVERVIEW_POSITION=THOUGHT>FPS_FRAME_JANK>CPU_GPU_SKIN_BATTERY>NETWORK>HERMES_H2')
print('R29_METRIC_IMPLEMENTATION_CHANGE=NONE')
print('R29_THERMAL_IMPLEMENTATION_CHANGE=NONE')
print('R29_NETWORK_IMPLEMENTATION_CHANGE=NONE')
print('R29_BACKEND_CHANGE=NONE')
print('R29_LAYOUT_CHANGE=DISPLAY_ORDER_ONLY')
