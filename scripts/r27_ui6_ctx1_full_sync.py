#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

# CTX1 FULL SYNC is additive on top of the proven UI6 FIX2 runtime contract.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-ctx1"',bs,count=1)
b.write_text(bs)

# Map all six CTX1 sections from the same already-authoritative cc_snapshot read.
cs=mapper.read_text()
field_anchor='        val supervisor: String,\n'
assert field_anchor in cs, 'CTX1_UI_FAIL=mapper-field-anchor'
ctx_fields=(
'        val hermesCtx1Status: String,\n'
'        val hermesCtx1Runtime: String,\n'
'        val hermesCtx1Safety: String,\n'
'        val hermesCtx1Hardware: String,\n'
'        val hermesCtx1Memory: String,\n'
'        val hermesCtx1Learning: String,\n'
)
if 'val hermesCtx1Status: String,' not in cs:
    cs=cs.replace(field_anchor,field_anchor+ctx_fields,1)
map_anchor='            supervisor = s["SUPERVISOR"].orEmpty(),\n'
assert map_anchor in cs, 'CTX1_UI_FAIL=mapper-map-anchor'
ctx_map=(
'            hermesCtx1Status = s["HERMES_CTX1_STATUS"].orEmpty(),\n'
'            hermesCtx1Runtime = s["HERMES_CTX1_RUNTIME"].orEmpty(),\n'
'            hermesCtx1Safety = s["HERMES_CTX1_SAFETY"].orEmpty(),\n'
'            hermesCtx1Hardware = s["HERMES_CTX1_HARDWARE"].orEmpty(),\n'
'            hermesCtx1Memory = s["HERMES_CTX1_MEMORY"].orEmpty(),\n'
'            hermesCtx1Learning = s["HERMES_CTX1_LEARNING"].orEmpty(),\n'
)
if 'hermesCtx1Status = s["HERMES_CTX1_STATUS"].orEmpty(),' not in cs:
    cs=cs.replace(map_anchor,map_anchor+ctx_map,1)
mapper.write_text(cs)

# RuntimeState receives the already-mapped CTX1 sections; no extra su/root/file read.
rs=r.read_text()
state_anchor='val supervisor:String=""'
assert state_anchor in rs, 'CTX1_UI_FAIL=runtime-state-anchor'
if 'val hermesCtx1Status:String=""' not in rs:
    rs=rs.replace(state_anchor,state_anchor+',val hermesCtx1Status:String="",val hermesCtx1Runtime:String="",val hermesCtx1Safety:String="",val hermesCtx1Hardware:String="",val hermesCtx1Memory:String="",val hermesCtx1Learning:String=""',1)
repo_anchor='supervisor=mapped.supervisor,'
assert repo_anchor in rs, 'CTX1_UI_FAIL=repository-map-anchor'
if 'hermesCtx1Status=mapped.hermesCtx1Status' not in rs:
    rs=rs.replace(repo_anchor,repo_anchor+'hermesCtx1Status=mapped.hermesCtx1Status,hermesCtx1Runtime=mapped.hermesCtx1Runtime,hermesCtx1Safety=mapped.hermesCtx1Safety,hermesCtx1Hardware=mapped.hermesCtx1Hardware,hermesCtx1Memory=mapped.hermesCtx1Memory,hermesCtx1Learning=mapped.hermesCtx1Learning,',1)

start=rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){')
end=rs.index('    suspend fun setUserMode',start)
snap=rs[start:end]
for required in ['ConsolidatedSnapshotReader','hermesCtx1Status=mapped.hermesCtx1Status','hermesCtx1Runtime=mapped.hermesCtx1Runtime','hermesCtx1Safety=mapped.hermesCtx1Safety','hermesCtx1Hardware=mapped.hermesCtx1Hardware','hermesCtx1Memory=mapped.hermesCtx1Memory','hermesCtx1Learning=mapped.hermesCtx1Learning']:
    assert required in snap, 'CTX1_UI_FAIL=snapshot-'+required
for forbidden in ['/sys/','hermes_vnext','current.context','context-vnext','djaeger-hermes-context-vnext','ProcessBuilder']:
    assert forbidden not in snap, 'CTX1_UI_FAIL=extra-recurring-read-'+forbidden
r.write_text(rs)

ms=m.read_text()
old='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2 • HERMES H2 RT3 FIX2'
new='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-ctx1 • HERMES H2 RT3 FIX2 • CTX1 FULL SYNC'
assert old in ms, 'CTX1_UI_FAIL=header-anchor'
ms=ms.replace(old,new,1)

# Add one UI6-native card containing every CTX1 context family. Raw module-published
# truth remains copyable and no presentation inference is invented by the APK.
strategy_anchor='@Composable fun StrategyCard(s:RuntimeState)'
assert strategy_anchor in ms, 'CTX1_UI_FAIL=strategy-anchor'
if '@Composable fun ContextVNextCard(s:RuntimeState)' not in ms:
    card=r'''@Composable fun ContextVNextCard(s:RuntimeState){
    fun ctx(raw:String,missing:String)=raw.trim().ifBlank{missing}
    val status=ctx(s.hermesCtx1Status,"UNAVAILABLE — CTX1 status not published.")
    val runtime=ctx(s.hermesCtx1Runtime,"UNAVAILABLE — CTX1 runtime context not published.")
    val safety=ctx(s.hermesCtx1Safety,"UNAVAILABLE — CTX1 safety context not published.")
    val hardware=ctx(s.hermesCtx1Hardware,"UNAVAILABLE — CTX1 hardware context not published.")
    val memory=ctx(s.hermesCtx1Memory,"UNAVAILABLE — CTX1 memory context not published.")
    val learning=ctx(s.hermesCtx1Learning,"UNAVAILABLE — CTX1 learning context not published.")
    val body="STATUS\n$status\n\nRUNTIME\n$runtime\n\nSAFETY\n$safety\n\nHARDWARE\n$hardware\n\nMEMORY\n$memory\n\nLEARNING\n$learning"
    BoxCard("HERMES CTX1 • CONTEXT VNEXT • SHADOW",body,true)
}

'''
    ms=ms.replace(strategy_anchor,card+strategy_anchor,1)
old_order='StatusCard(s);ThoughtsCard(s);HermesCard(s);StrategyCard(s);OutcomeLearningCard(s);'
new_order='StatusCard(s);ThoughtsCard(s);HermesCard(s);ContextVNextCard(s);StrategyCard(s);OutcomeLearningCard(s);'
assert old_order in ms, 'CTX1_UI_FAIL=overview-order-anchor'
ms=ms.replace(old_order,new_order,1)

# Preserve authority boundaries and UI6 safety.
for required in ['HERMES CTX1 • CONTEXT VNEXT • SHADOW','s.hermesCtx1Status','s.hermesCtx1Runtime','s.hermesCtx1Safety','s.hermesCtx1Hardware','s.hermesCtx1Memory','s.hermesCtx1Learning']:
    assert required in ms, required
for forbidden in ['/sys/','iptables','ip6tables','settings put','setprop','force-stop','djaeger-root-authority','djaeger-hermes-context-vnext','ProcessBuilder']:
    assert forbidden not in card, forbidden
m.write_text(ms)

# Final full-sync contract gates.
cs=mapper.read_text(); rs=r.read_text(); ms=m.read_text()
for sec in ['STATUS','RUNTIME','SAFETY','HARDWARE','MEMORY','LEARNING']:
    assert f's["HERMES_CTX1_{sec}"]' in cs, sec
assert new_order in ms
print('CTX1_UI_BASELINE=UI6_FIX2')
print('CTX1_UI_SECTIONS=STATUS,RUNTIME,SAFETY,HARDWARE,MEMORY,LEARNING')
print('CTX1_UI_SINGLE_ATOMIC_CC_SNAPSHOT_READ=PASS')
print('CTX1_UI_EXTRA_ROOT_READS=0')
print('CTX1_UI_HARDWARE_AUTHORITY_CHANGE=NONE')
print('CTX1_UI_NETWORK_GAME_TRAFFIC_CHANGE=NONE')
print('CTX1_UI6_LAYOUT_FAMILY=PRESERVED')
