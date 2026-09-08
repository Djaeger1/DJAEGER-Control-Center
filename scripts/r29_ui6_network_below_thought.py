#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12232',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-cog1-netorder"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
old_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1 • HERMES COGNITION VNEXT'
new_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-netorder • HERMES COGNITION VNEXT'
assert old_header in ms, 'R29_FAIL=header-anchor'
ms=ms.replace(old_header,new_header,1)

# NETWORK is display-only and already exists exactly once in Overview.
# Move only its call: below THOUGHT, above HERMES H2. Do not alter NetworkCard itself.
assert ms.count('NetworkCard(s.network);') == 1, 'R29_FAIL=network-call-count'
ms=ms.replace('NetworkCard(s.network);','',1)
anchor='ThoughtsCard(s);HermesCard(s);'
assert anchor in ms, 'R29_FAIL=thought-hermes-anchor'
ms=ms.replace(anchor,'ThoughtsCard(s);NetworkCard(s.network);HermesCard(s);',1)

# Exact requested hierarchy.
requested='StatusCard(s);ThoughtsCard(s);NetworkCard(s.network);HermesCard(s);ContextVNextCard(s);MemoryVNextCard(s);ReasoningV2Card(s);SkillsVNextCard(s);LearningResearchV2Card(s);StrategyCard(s);OutcomeLearningCard(s);'
assert requested in ms, 'R29_FAIL=requested-order'
assert ms.count('NetworkCard(s.network);') == 1, 'R29_FAIL=network-duplicate'

# Nothing about network collection or backend authority changes here.
for forbidden in ['iptables','ip6tables','settings put','setprop','force-stop','/sys/','ProcessBuilder']:
    assert forbidden not in ms[ms.index('@Composable fun NetworkCard'):ms.index('@Composable fun', ms.index('@Composable fun NetworkCard')+1)] if '@Composable fun NetworkCard' in ms and ms.find('@Composable fun', ms.index('@Composable fun NetworkCard')+1) != -1 else True

m.write_text(ms)
print('R29_NETWORK_POSITION=THOUGHT>NETWORK>HERMES_H2')
print('R29_NETWORK_CARD_IMPLEMENTATION_CHANGE=NONE')
print('R29_NETWORK_BACKEND_CHANGE=NONE')
print('R29_HERMES_BACKEND_CHANGE=NONE')
print('R29_LAYOUT_CHANGE=NETWORK_CALL_ONLY')
