#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12231',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-cog1"',bs,count=1)
b.write_text(bs)

cs=mapper.read_text()
field_anchor='        val hermesCtx1Learning: String,\n'
assert field_anchor in cs
fields='''        val hermesCognitionStatus: String,\n        val hermesMemoryVNext: String,\n        val hermesReasoningV2: String,\n        val hermesSkillsVNext: String,\n        val hermesLearningV2: String,\n        val hermesResearchV2: String,\n'''
if 'val hermesCognitionStatus: String,' not in cs:
    cs=cs.replace(field_anchor,field_anchor+fields,1)
map_anchor='            hermesCtx1Learning = s["HERMES_CTX1_LEARNING"].orEmpty(),\n'
assert map_anchor in cs
maps='''            hermesCognitionStatus = s["HERMES_COGNITION_STATUS"].orEmpty(),\n            hermesMemoryVNext = s["HERMES_MEMORY_VNEXT"].orEmpty(),\n            hermesReasoningV2 = s["HERMES_REASONING_V2"].orEmpty(),\n            hermesSkillsVNext = s["HERMES_SKILLS_VNEXT"].orEmpty(),\n            hermesLearningV2 = s["HERMES_LEARNING_V2"].orEmpty(),\n            hermesResearchV2 = s["HERMES_RESEARCH_V2"].orEmpty(),\n'''
if 'hermesCognitionStatus = s["HERMES_COGNITION_STATUS"].orEmpty(),' not in cs:
    cs=cs.replace(map_anchor,map_anchor+maps,1)
mapper.write_text(cs)

rs=r.read_text()
state_anchor='val hermesCtx1Learning:String=""'
assert state_anchor in rs
if 'val hermesCognitionStatus:String=""' not in rs:
    rs=rs.replace(state_anchor,state_anchor+',val hermesCognitionStatus:String="",val hermesMemoryVNext:String="",val hermesReasoningV2:String="",val hermesSkillsVNext:String="",val hermesLearningV2:String="",val hermesResearchV2:String=""',1)
repo_anchor='hermesCtx1Learning=mapped.hermesCtx1Learning,'
assert repo_anchor in rs
if 'hermesCognitionStatus=mapped.hermesCognitionStatus' not in rs:
    rs=rs.replace(repo_anchor,repo_anchor+'hermesCognitionStatus=mapped.hermesCognitionStatus,hermesMemoryVNext=mapped.hermesMemoryVNext,hermesReasoningV2=mapped.hermesReasoningV2,hermesSkillsVNext=mapped.hermesSkillsVNext,hermesLearningV2=mapped.hermesLearningV2,hermesResearchV2=mapped.hermesResearchV2,',1)
start=rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){')
end=rs.index('    suspend fun setUserMode',start)
snap=rs[start:end]
for x in ['ConsolidatedSnapshotReader','hermesMemoryVNext=mapped.hermesMemoryVNext','hermesReasoningV2=mapped.hermesReasoningV2','hermesSkillsVNext=mapped.hermesSkillsVNext','hermesLearningV2=mapped.hermesLearningV2','hermesResearchV2=mapped.hermesResearchV2']:
    assert x in snap,x
for x in ['/sys/','hermes_vnext','cognition','semantic_memory.tsv','ProcessBuilder']:
    assert x not in snap,x
r.write_text(rs)

ms=m.read_text()
old='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-ctx1 • HERMES H2 RT3 FIX2 • CTX1 FULL SYNC'
new='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1 • HERMES COGNITION VNEXT'
assert old in ms
ms=ms.replace(old,new,1)
anchor='@Composable fun StrategyCard(s:RuntimeState)'
assert anchor in ms
if '@Composable fun MemoryVNextCard' not in ms:
    cards=r'''@Composable fun MemoryVNextCard(s:RuntimeState){
    val status=s.hermesCognitionStatus.trim().ifBlank{"STATE=UNAVAILABLE"}
    val body=s.hermesMemoryVNext.trim().ifBlank{"STATE=UNAVAILABLE — Memory vNext has not published yet."}
    BoxCard("HERMES • MEMORY VNEXT",status+"\n\n"+body,true)
}

@Composable fun ReasoningV2Card(s:RuntimeState){
    val body=s.hermesReasoningV2.trim().ifBlank{"STATE=UNAVAILABLE — Reasoning v2 has not published yet."}
    BoxCard("HERMES • REASONING V2",body,true)
}

@Composable fun SkillsVNextCard(s:RuntimeState){
    val body=s.hermesSkillsVNext.trim().ifBlank{"STATE=UNAVAILABLE — Skills vNext has not published yet."}
    BoxCard("HERMES • SKILLS VNEXT",body,true)
}

@Composable fun LearningResearchV2Card(s:RuntimeState){
    val learning=s.hermesLearningV2.trim().ifBlank{"STATE=UNAVAILABLE — Learning v2 has not published yet."}
    val research=s.hermesResearchV2.trim().ifBlank{"STATE=UNAVAILABLE — Research v2 has not published yet."}
    BoxCard("HERMES • LEARNING + RESEARCH V2","LEARNING\n$learning\n\nRESEARCH\n$research",true)
}

'''
    ms=ms.replace(anchor,cards+anchor,1)
old_order='StatusCard(s);ThoughtsCard(s);HermesCard(s);ContextVNextCard(s);StrategyCard(s);OutcomeLearningCard(s);'
new_order='StatusCard(s);ThoughtsCard(s);HermesCard(s);ContextVNextCard(s);MemoryVNextCard(s);ReasoningV2Card(s);SkillsVNextCard(s);LearningResearchV2Card(s);StrategyCard(s);OutcomeLearningCard(s);'
assert old_order in ms
ms=ms.replace(old_order,new_order,1)
for x in ['HERMES • MEMORY VNEXT','HERMES • REASONING V2','HERMES • SKILLS VNEXT','HERMES • LEARNING + RESEARCH V2']:
    assert x in ms
for x in ['/sys/','iptables','ip6tables','settings put','setprop','force-stop','djaeger-root-authority','djaeger-hermes-cognition-vnext','ProcessBuilder']:
    assert x not in cards,x
m.write_text(ms)

cs=mapper.read_text();rs=r.read_text();ms=m.read_text()
for sec in ['HERMES_COGNITION_STATUS','HERMES_MEMORY_VNEXT','HERMES_REASONING_V2','HERMES_SKILLS_VNEXT','HERMES_LEARNING_V2','HERMES_RESEARCH_V2']:
    assert f's["{sec}"]' in cs,sec
assert new_order in ms
print('COG1_UI_BASELINE=UI6_FIX2_CTX1_FULLSYNC')
print('COG1_UI_MEMORY_VNEXT=PASS')
print('COG1_UI_REASONING_V2=PASS')
print('COG1_UI_SKILLS_VNEXT=PASS')
print('COG1_UI_LEARNING_V2=PASS')
print('COG1_UI_RESEARCH_V2=PASS')
print('COG1_UI_SINGLE_ATOMIC_CC_SNAPSHOT_READ=PASS')
print('COG1_UI_EXTRA_ROOT_READS=0')
print('COG1_UI_EXECUTION_AUTHORITY_CHANGE=NONE')
print('COG1_UI_NETWORK_GAME_TRAFFIC_CHANGE=NONE')
