#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12240',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r24"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# R24 deliberately binds to the stable R20+ runtime boundary: MEMORY -> AUTHORITY.
# This avoids fragile assumptions about the older BRAIN shell marker while preserving
# the already-proven R19 thoughts/memory parser and R20-R23 authority/session fields.
state=re.search(r'data class RuntimeState\((.*?)\)',rs,re.S); assert state,'RuntimeState missing'
if 'runtimeVersion:String' not in state.group(1):
    rs=rs[:state.start(1)]+'runtimeVersion:String="",'+rs[state.start(1):]
# Add canonical module runtime identity between MEMORY and AUTHORITY in the generated shell.
old="echo __MEMORY__; cat '$persistent/local_memory_status.env' 2>/dev/null\n        echo __AUTHORITY__;"
new="echo __MEMORY__; cat '$persistent/local_memory_status.env' 2>/dev/null\n        echo __RUNTIME_VERSION__; cat '$persistent/runtime_version.env' 2>/dev/null\n        echo __AUTHORITY__;"
assert old in rs,'stable MEMORY->AUTHORITY snapshot boundary missing'
rs=rs.replace(old,new,1)
# Re-slice MEMORY at RUNTIME_VERSION and expose the canonical version section.
oldp='memoryStatus=section("MEMORY","AUTHORITY").trim(),authority=section("AUTHORITY","SESSION_SAFETY").trim()'
newp='memoryStatus=section("MEMORY","RUNTIME_VERSION").trim(),runtimeVersion=section("RUNTIME_VERSION","AUTHORITY").trim(),authority=section("AUTHORITY","SESSION_SAFETY").trim()'
assert oldp in rs,'stable MEMORY->AUTHORITY parser boundary missing'
rs=rs.replace(oldp,newp,1)
r.write_text(rs)
ms=m.read_text().replace('v0.12.1-r23','v0.12.1-r24').replace('R87 RUNTIME RECONCILE','CANONICAL RUNTIME READER')
# Keep identity parser available for UI/debugging; do not fabricate a module version.
anchor='private fun thoughtField('
assert anchor in ms,'thoughtField anchor missing'
helper='''private fun runtimeField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\\'') ?: ""\nprivate fun runtimeIdentity(s:RuntimeState):String {\n    val v=runtimeField(s.runtimeVersion,"MODULE_VERSION")\n    val label=runtimeField(s.runtimeVersion,"RUNTIME_LABEL")\n    return listOf(v,label).filter{it.isNotBlank()}.joinToString(" • ").ifBlank{"RUNTIME WAITING"}\n}\n\n'''
if 'fun runtimeIdentity' not in ms: ms=ms.replace(anchor,helper+anchor,1)
ms=ms.replace('R87','RUNTIME')
m.write_text(ms)
R=r.read_text(); M=m.read_text()
for x in ['runtime_version.env','__RUNTIME_VERSION__','runtimeVersion=section("RUNTIME_VERSION","AUTHORITY")','djaeger_thoughts.env','local_memory_status.env','authority_state.env','session_safety.env']: assert x in R,x
assert 'R87 RUNTIME RECONCILE' not in M
assert '0.12.1-r24' in b.read_text()
forbidden=['/sys/class/net','iptables ','ip6tables ','nft ','tc qdisc','settings put global private_dns']
assert not any(x in R for x in forbidden)
print('R24_CANONICAL_RUNTIME_VERSION=PASS')
print('R24_STABLE_BOUNDARY=MEMORY_TO_AUTHORITY')
print('R24_THOUGHTS_MEMORY_READER=PRESERVED')
print('R24_AUTHORITY_SESSION_READER=PRESERVED')
print('R24_NETWORK_NON_INTERFERENCE=PASS')
