#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12240',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r24"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# R24 reads the exact canonical files proven on-device under /data/adb/djaeger_ai.
# Keep this read-only: Control Center never becomes an actuator.
old="echo __BRAIN__; cat '$persistent/local_brain_state' 2>/dev/null"
new="""echo __RUNTIME_VERSION__; cat '$persistent/runtime_version.env' 2>/dev/null
        echo __BRAIN__; cat '$persistent/local_brain_state' 2>/dev/null"""
if '__RUNTIME_VERSION__' not in rs:
    assert old in rs, 'brain snapshot anchor missing'
    rs=rs.replace(old,new,1)
# Extend state without disturbing existing call sites: default keeps source compatibility.
state=re.search(r'data class RuntimeState\((.*?)\)\s*\{?',rs,re.S)
assert state, 'RuntimeState missing'
if 'runtimeVersion:String' not in state.group(1):
    rs=rs[:state.start(1)]+'runtimeVersion:String="",'+rs[state.start(1):]
# Parser must consume the new section boundary rather than leaking version text into LIVE/BRAIN.
rs=rs.replace('brain=section("BRAIN","THOUGHTS").trim()', 'runtimeVersion=section("RUNTIME_VERSION","BRAIN").trim(),brain=section("BRAIN","THOUGHTS").trim()',1)
assert 'runtimeVersion=section("RUNTIME_VERSION","BRAIN")' in rs
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('v0.12.1-r23','v0.12.1-r24')
ms=ms.replace('R87 RUNTIME RECONCILE','CANONICAL RUNTIME READER')
# Dynamic backend identity helper. It uses only module-published runtime_version.env.
helper='''\nprivate fun runtimeField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\\'') ?: ""\nprivate fun runtimeIdentity(s:RuntimeState):String {\n    val v=runtimeField(s.runtimeVersion,"MODULE_VERSION")\n    val label=runtimeField(s.runtimeVersion,"RUNTIME_LABEL")\n    return listOf(v,label).filter{it.isNotBlank()}.joinToString(" • ").ifBlank{"RUNTIME WAITING"}\n}\n'''
anchor='private fun thoughtField('
assert anchor in ms
if 'fun runtimeIdentity' not in ms: ms=ms.replace(anchor,helper+'\n'+anchor,1)
# Preserve visual layout; replace static R87 text wherever it survived transforms.
ms=ms.replace('R87','RUNTIME')
m.write_text(ms)
# Regression assertions tied to the actual R90 device contract.
R=r.read_text(); M=m.read_text()
for x in ['runtime_version.env','local_brain_state','djaeger_thoughts.env','local_memory_status.env','session_safety.env','__RUNTIME_VERSION__']:
    assert x in R,x
assert 'R87 RUNTIME RECONCILE' not in M
assert '0.12.1-r24' in b.read_text()
forbidden=['/sys/class/net','iptables ','ip6tables ','nft ','tc qdisc','settings put global private_dns']
assert not any(x in R for x in forbidden)
print('R24_CANONICAL_RUNTIME_VERSION=PASS'); print('R24_THOUGHTS_MEMORY_READER=PRESERVED'); print('R24_NETWORK_NON_INTERFERENCE=PASS'); print('R24_AUTHORITY=READ_ONLY')
