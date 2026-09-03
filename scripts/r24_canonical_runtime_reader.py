#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12240',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r24"',bs,count=1); b.write_text(bs)
rs=r.read_text()
state=re.search(r'data class RuntimeState\((.*?)\)',rs,re.S); assert state,'RuntimeState missing'
if 'runtimeVersion:String' not in state.group(1): rs=rs[:state.start(1)]+'runtimeVersion:String="",'+rs[state.start(1):]
class_anchor='class DjaegerRepository'; pos=rs.find(class_anchor); assert pos>=0,'repository class missing'; brace=rs.find('{',pos); assert brace>=0,'repository class brace missing'
reader='''\n    private suspend fun readRuntimeVersion():String = withContext(Dispatchers.IO) {\n        root("cat /data/adb/djaeger_ai/runtime_version.env 2>/dev/null").out.trim()\n    }\n'''
if 'fun readRuntimeVersion()' not in rs: rs=rs[:brace+1]+reader+rs[brace+1:]
# R9's generated snapshot ends in a named-argument RuntimeState constructor. Bind
# canonical runtime identity directly there instead of relying on a return keyword.
needle='RuntimeState(\n            root=true,'
assert needle in rs,'R9 RuntimeState constructor boundary missing'
rs=rs.replace(needle,'RuntimeState(\n            runtimeVersion=readRuntimeVersion(),\n            root=true,',1)
r.write_text(rs)
ms=m.read_text().replace('v0.12.1-r23','v0.12.1-r24').replace('R87 RUNTIME RECONCILE','CANONICAL RUNTIME READER').replace('R87','RUNTIME')
anchor='private fun thoughtField('; assert anchor in ms,'thoughtField missing'
helper='''private fun runtimeField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\\'') ?: ""\nprivate fun runtimeIdentity(s:RuntimeState):String {\n    val v=runtimeField(s.runtimeVersion,"MODULE_VERSION")\n    val label=runtimeField(s.runtimeVersion,"RUNTIME_LABEL")\n    return listOf(v,label).filter{it.isNotBlank()}.joinToString(" • ").ifBlank{"RUNTIME WAITING"}\n}\n\n'''
if 'fun runtimeIdentity' not in ms: ms=ms.replace(anchor,helper+anchor,1)
m.write_text(ms)
R=r.read_text(); M=m.read_text()
for x in ['runtime_version.env','runtimeVersion:String','runtimeVersion=readRuntimeVersion()','djaeger_thoughts.env','local_memory_status.env','authority_state.env','session_safety.env']: assert x in R,x
assert 'R87 RUNTIME RECONCILE' not in M
forbidden=['/sys/class/net','iptables ','ip6tables ','nft ','tc qdisc','settings put global private_dns']; assert not any(x in R for x in forbidden)
print('R24_CANONICAL_RUNTIME_VERSION=BOUND'); print('R24_R9_STATE_CONSTRUCTOR=PASS'); print('R24_THOUGHTS_MEMORY_READER=PRESERVED'); print('R24_AUTHORITY_SESSION_READER=PRESERVED'); print('R24_NETWORK_NON_INTERFERENCE=PASS')
