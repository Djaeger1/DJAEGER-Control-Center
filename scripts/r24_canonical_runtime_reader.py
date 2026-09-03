#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12240',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r24"',bs,count=1)
b.write_text(bs)

# R90 publishes VERSION, THOUGHTS, MEMORY, AUTHORITY, SESSION_SAFETY and
# SUPERVISOR inside the single atomic cc_snapshot. Extend the R9 mapper instead
# of restoring the retired multi-read shell snapshot.
mp=mapper.read_text()
field_anchor='        val reasoning: String,'
assert field_anchor in mp,'Mapped field anchor missing'
fields='''        val thoughts: String,\n        val memoryStatus: String,\n        val authority: String,\n        val sessionSafety: String,\n        val supervisor: String,\n'''
if 'val thoughts: String' not in mp:
    mp=mp.replace(field_anchor,fields+field_anchor,1)
assign_anchor='            reasoning = s["REASONING"].orEmpty(),'
assert assign_anchor in mp,'mapper assignment anchor missing'
assigns='''            thoughts = s["THOUGHTS"].orEmpty(),\n            memoryStatus = s["MEMORY"].orEmpty(),\n            authority = s["AUTHORITY"].orEmpty(),\n            sessionSafety = s["SESSION_SAFETY"].orEmpty(),\n            supervisor = s["SUPERVISOR"].orEmpty(),\n'''
if 'thoughts = s["THOUGHTS"]' not in mp:
    mp=mp.replace(assign_anchor,assigns+assign_anchor,1)
mapper.write_text(mp)

rs=r.read_text()
# R19/R20 already add thoughts/memory/authority/session/supervisor fields.
# Assert them instead of re-adding them. Only runtimeVersion is new in R24.
for existing in ['val thoughts:String=""','val memoryStatus:String=""','val authority:String=""','val sessionSafety:String=""','val supervisor:String=""']:
    assert existing in rs,existing+' missing after R19/R20 chain'
if 'val runtimeVersion:String=""' not in rs:
    anchor='data class RuntimeState('
    assert anchor in rs,'RuntimeState missing'
    rs=rs.replace(anchor,anchor+'val runtimeVersion:String="",',1)

class_anchor='class DjaegerRepository'
pos=rs.find(class_anchor); assert pos>=0,'repository class missing'
brace=rs.find('{',pos); assert brace>=0,'repository class brace missing'
helper='''\n    private fun canonicalRuntimeVersion(moduleVersion:String):String =\n        "MODULE_VERSION='${moduleVersion.trim()}'"\n'''
if 'fun canonicalRuntimeVersion(' not in rs:
    rs=rs[:brace+1]+helper+rs[brace+1:]

needle='RuntimeState(\n            root=true,'
assert needle in rs,'R9 RuntimeState constructor boundary missing'
bind='''RuntimeState(\n            runtimeVersion=canonicalRuntimeVersion(mapped.moduleVersion),\n            thoughts=mapped.thoughts,\n            memoryStatus=mapped.memoryStatus,\n            authority=mapped.authority,\n            sessionSafety=mapped.sessionSafety,\n            supervisor=mapped.supervisor,\n            root=true,'''
rs=rs.replace(needle,bind,1)
r.write_text(rs)

ms=m.read_text().replace('v0.12.1-r23','v0.12.1-r24').replace('R87 RUNTIME RECONCILE','CANONICAL RUNTIME READER').replace('R87','RUNTIME')
anchor='private fun thoughtField('
assert anchor in ms,'thoughtField missing'
helper_ui='''private fun runtimeField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\\'') ?: ""\nprivate fun runtimeIdentity(s:RuntimeState):String {\n    val v=runtimeField(s.runtimeVersion,"MODULE_VERSION")\n    return v.ifBlank{s.moduleVersion.ifBlank{"RUNTIME WAITING"}}\n}\n\n'''
if 'fun runtimeIdentity' not in ms:
    ms=ms.replace(anchor,helper_ui+anchor,1)
needle_ui='StatusCard(s);ThoughtsCard(s);Row(Modifier.fillMaxWidth()'
assert needle_ui in ms,'Overview Thoughts anchor missing'
ms=ms.replace(needle_ui,'StatusCard(s);ThoughtsCard(s);BoxCard("RUNTIME IDENTITY",runtimeIdentity(s),true);Row(Modifier.fillMaxWidth()',1)
m.write_text(ms)

R=r.read_text(); MP=mapper.read_text(); M=m.read_text()
for x in ['runtimeVersion=canonicalRuntimeVersion(mapped.moduleVersion)','thoughts=mapped.thoughts','memoryStatus=mapped.memoryStatus','authority=mapped.authority','sessionSafety=mapped.sessionSafety','supervisor=mapped.supervisor']:
    assert x in R,x
for x in ['s["THOUGHTS"]','s["MEMORY"]','s["AUTHORITY"]','s["SESSION_SAFETY"]','s["SUPERVISOR"]']:
    assert x in MP,x
for name in ['thoughts','memoryStatus','authority','sessionSafety','supervisor']:
    assert R.count('val '+name+':String=""') == 1,(name+' field count')
assert 'BoxCard("RUNTIME IDENTITY",runtimeIdentity(s),true)' in M
assert 'ProcessBuilder("su"' not in MP,'mapper must not spawn a second root process'
assert 'R87 RUNTIME RECONCILE' not in M
forbidden=['/sys/class/net','iptables ','ip6tables ','nft ','tc qdisc','settings put global private_dns']
assert not any(x in R+MP for x in forbidden)
print('R24_RUNTIME_IDENTITY=CC_SNAPSHOT_VERSION_BOUND')
print('R24_THOUGHTS_MEMORY=CC_SNAPSHOT_BOUND')
print('R24_AUTHORITY_SESSION=CC_SNAPSHOT_BOUND')
print('R24_SUPERVISOR=CC_SNAPSHOT_BOUND')
print('R24_FIELD_DUPLICATION_GUARD=PASS')
print('R24_SINGLE_SNAPSHOT_ARCHITECTURE=PRESERVED')
print('R24_RUNTIME_IDENTITY_VISIBLE=PASS')
print('R24_NETWORK_NON_INTERFERENCE=PASS')
