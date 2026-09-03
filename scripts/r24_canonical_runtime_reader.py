#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12240',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r24"',bs,count=1); b.write_text(bs)
rs=r.read_text()
state=re.search(r'data class RuntimeState\((.*?)\)',rs,re.S); assert state,'RuntimeState missing'
fields=state.group(1)
# Ensure first-class canonical publication fields exist even when older R19/R20
# shell-marker replacements were silently bypassed by the R9 cutover.
need=[('runtimeVersion','String=""'),('thoughts','String=""'),('memoryStatus','String=""'),('authority','String=""'),('sessionSafety','String=""')]
insert=''
for name,typ in need:
    if f'{name}:' not in fields: insert += f'val {name}:{typ},'
if insert:
    rs=rs[:state.start(1)]+insert+rs[state.start(1):]

# R24 keeps the R9 invariant: recurring UI refresh consumes only cc_snapshot.
# Extend the mapper to expose canonical sections already published by DJAEGER.
mp=mapper.read_text()
mapped=re.search(r'data class Mapped\((.*?)\n\s*\)',mp,re.S); assert mapped,'Mapped data class missing'
minsert=''
for name in ['runtimeVersion','thoughts','memoryStatus','authority','sessionSafety']:
    if f'val {name}: String' not in mapped.group(1): minsert += f'        val {name}: String,\n'
if minsert:
    mp=mp[:mapped.start(1)]+mapped.group(1)+"\n"+minsert+mp[mapped.end(1):]
# Bind each field from AtomicSnapshot sections. No additional su/root process.
anchor='            brain = s["BRAIN"].orEmpty(),'
assert anchor in mp,'mapper BRAIN anchor missing'
extra='''            runtimeVersion = s["RUNTIME_VERSION"].orEmpty(),\n            thoughts = s["THOUGHTS"].orEmpty(),\n            memoryStatus = s["MEMORY"].orEmpty(),\n            authority = s["AUTHORITY"].orEmpty(),\n            sessionSafety = s["SESSION_SAFETY"].orEmpty(),\n'''
if 'runtimeVersion = s["RUNTIME_VERSION"]' not in mp:
    mp=mp.replace(anchor,extra+anchor,1)
mapper.write_text(mp)

# Bind mapper fields into the R9 RuntimeState constructor.
needle='RuntimeState(\n            root=true,'
assert needle in rs,'R9 RuntimeState constructor boundary missing'
bind='''RuntimeState(\n            runtimeVersion=mapped.runtimeVersion,\n            thoughts=mapped.thoughts,\n            memoryStatus=mapped.memoryStatus,\n            authority=mapped.authority,\n            sessionSafety=mapped.sessionSafety,\n            root=true,'''
rs=rs.replace(needle,bind,1)
r.write_text(rs)

ms=m.read_text().replace('v0.12.1-r23','v0.12.1-r24').replace('R87 RUNTIME RECONCILE','CANONICAL RUNTIME READER').replace('R87','RUNTIME')
anchor='private fun thoughtField('; assert anchor in ms,'thoughtField missing'
helper='''private fun runtimeField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\\'') ?: ""\nprivate fun runtimeIdentity(s:RuntimeState):String {\n    val v=runtimeField(s.runtimeVersion,"MODULE_VERSION")\n    val label=runtimeField(s.runtimeVersion,"RUNTIME_LABEL")\n    return listOf(v,label).filter{it.isNotBlank()}.joinToString(" • ").ifBlank{"RUNTIME WAITING"}\n}\n\n'''
if 'fun runtimeIdentity' not in ms: ms=ms.replace(anchor,helper+anchor,1)
# Show actual backend identity in the header; never hard-code R90/R89.
if '${runtimeIdentity(state)}' not in ms:
    ms=re.sub(r'Text\("(CONTROL CENTER • v0\.12\.1-r24[^"$]*)"\s*,color=Muted\)',r'Text("\1 • ${runtimeIdentity(state)}",color=Muted)',ms,count=1)
m.write_text(ms)

R=r.read_text(); MP=mapper.read_text(); M=m.read_text()
for x in ['runtimeVersion=mapped.runtimeVersion','thoughts=mapped.thoughts','memoryStatus=mapped.memoryStatus','authority=mapped.authority','sessionSafety=mapped.sessionSafety']: assert x in R,x
for x in ['s["RUNTIME_VERSION"]','s["THOUGHTS"]','s["MEMORY"]','s["AUTHORITY"]','s["SESSION_SAFETY"]']: assert x in MP,x
assert '${runtimeIdentity(state)}' in M,'runtime identity not visible in header'
assert 'ProcessBuilder("su"' not in MP,'mapper must not spawn root process'
assert 'R87 RUNTIME RECONCILE' not in M
forbidden=['/sys/class/net','iptables ','ip6tables ','nft ','tc qdisc','settings put global private_dns']; assert not any(x in R for x in forbidden)
print('R24_CANONICAL_PUBLICATIONS=CC_SNAPSHOT_MAPPED')
print('R24_RECURRING_ROOT_READ=CC_SNAPSHOT_ONLY')
print('R24_THOUGHTS_MEMORY_READER=REAL_BINDING')
print('R24_AUTHORITY_SESSION_READER=REAL_BINDING')
print('R24_RUNTIME_IDENTITY=VISIBLE_DYNAMIC')
print('R24_NETWORK_NON_INTERFERENCE=PASS')
