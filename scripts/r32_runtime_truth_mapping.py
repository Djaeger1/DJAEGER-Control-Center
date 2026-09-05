#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

# Version: this is a real UI/runtime-contract bugfix, not a cosmetic bump.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12320',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r32"',bs,count=1)
b.write_text(bs)

# 1) Preserve the backend-published authority/session/supervisor sections that
# were already present in the single atomic cc_snapshot but were dropped by the
# consolidated mapper.
cs=mapper.read_text()
assert 'val providerStatus: String,' in cs, 'R32 mapper provider anchor missing'
if 'val authority: String,' not in cs:
    cs=cs.replace(
        'val providerStatus: String,',
        'val providerStatus: String,\n        val authority: String,\n        val sessionSafety: String,\n        val supervisor: String,',
        1,
    )
assert 'providerStatus = s["PROVIDERS"].orEmpty(),' in cs, 'R32 mapper providers section anchor missing'
if 'authority = s["AUTHORITY"].orEmpty(),' not in cs:
    cs=cs.replace(
        'providerStatus = s["PROVIDERS"].orEmpty(),',
        'providerStatus = s["PROVIDERS"].orEmpty(),\n            authority = s["AUTHORITY"].orEmpty(),\n            sessionSafety = s["SESSION_SAFETY"].orEmpty(),\n            supervisor = s["SUPERVISOR"].orEmpty(),',
        1,
    )
for required in [
    'val authority: String,',
    'val sessionSafety: String,',
    'val supervisor: String,',
    'authority = s["AUTHORITY"].orEmpty(),',
    'sessionSafety = s["SESSION_SAFETY"].orEmpty(),',
    'supervisor = s["SUPERVISOR"].orEmpty(),',
]:
    assert required in cs, 'R32 mapper closure missing: '+required
mapper.write_text(cs)

# 2) Wire those sections into RuntimeState without adding another root read.
rs=r.read_text()
for required in ['val authority:String=""','val sessionSafety:String=""','val supervisor:String=""']:
    assert required in rs, 'R32 RuntimeState field missing from preserved R20 contract: '+required
assert 'attributionStatus=mapped.attribution,' in rs, 'R32 attribution mapping anchor missing'
if 'authority=mapped.authority,' not in rs:
    rs=rs.replace(
        'attributionStatus=mapped.attribution,',
        'attributionStatus=mapped.attribution,\n            authority=mapped.authority,\n            sessionSafety=mapped.sessionSafety,\n            supervisor=mapped.supervisor,',
        1,
    )
for required in ['authority=mapped.authority,','sessionSafety=mapped.sessionSafety,','supervisor=mapped.supervisor,']:
    assert required in rs, 'R32 RuntimeState mapping missing: '+required

# 3) StrategyTruth originally looked only in runtime_status for learning/source.
# FIX3 publishes the authoritative fields in BRAIN and ATTRIBUTION inside the
# same cc_snapshot. Bind only those published values; never synthesize numbers.
strategy_anchor='        val strategy=StrategyTruth('
assert strategy_anchor in rs, 'R32 StrategyTruth anchor missing'
if 'val brainTruth = AtomicSnapshot.keyValues(mapped.brain)' not in rs:
    helper='''        val brainTruth = AtomicSnapshot.keyValues(mapped.brain)\n        val attributionTruth = AtomicSnapshot.keyValues(mapped.attribution)\n        fun published(vararg values:String?):String = values.firstOrNull { v ->\n            val x=v?.trim().orEmpty()\n            x.isNotBlank() && x!="—" && !x.equals("UNAVAILABLE",true)\n        }?.trim() ?: "—"\n\n'''
    rs=rs.replace(strategy_anchor,helper+strategy_anchor,1)

# R15 rewrote StrategyTruth, so bind against the R15 final anchors.
old='source=rv("DECISION_SOURCE","decision_source","SOURCE").let{if(it=="—") rv("SOURCE") else it}'
new='source=published(attributionTruth["REASONER_SOURCE"],brainTruth["SOURCE"],rv("DECISION_SOURCE","decision_source","SOURCE"))'
assert old in rs or new in rs, 'R32 decision source StrategyTruth anchor missing'
rs=rs.replace(old,new,1)

old='learningSamples=rv("LEARNING_SAMPLES","SAMPLES")'
new='learningSamples=published(brainTruth["LEARNED_SAMPLES"],rv("LEARNING_SAMPLES","SAMPLES"))'
assert old in rs or new in rs, 'R32 learning samples anchor missing'
rs=rs.replace(old,new,1)

old='learningConfidence=rv("LEARNING_CONFIDENCE","CONFIDENCE")'
new='learningConfidence=published(brainTruth["LEARNED_CONF"],rv("LEARNING_CONFIDENCE","CONFIDENCE"))'
assert old in rs or new in rs, 'R32 learning confidence anchor missing'
rs=rs.replace(old,new,1)

old='learningPromotion=rv("LEARNED_STATE","LEARNING_STATUS")'
new='learningPromotion=published(brainTruth["LEARNING_PROMOTION"],rv("LEARNED_STATE","LEARNING_STATUS"))'
assert old in rs or new in rs, 'R32 learning promotion anchor missing'
rs=rs.replace(old,new,1)

for required in [
    'attributionTruth["REASONER_SOURCE"]',
    'brainTruth["LEARNED_SAMPLES"]',
    'brainTruth["LEARNED_CONF"]',
    'brainTruth["LEARNING_PROMOTION"]',
]:
    assert required in rs, 'R32 truth binding missing: '+required

# Guard the recurring path: still exactly one atomic snapshot read, with no
# direct authority/session file polling introduced by this fix.
snapshot_start=rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){')
snapshot_end=rs.index('    suspend fun setUserMode',snapshot_start)
snapshot=rs[snapshot_start:snapshot_end]
assert 'ConsolidatedSnapshotReader' in snapshot
for forbidden in [
    'authority_sync_boot.log','authority_state.env','session_recovery_state',
    'session_safety.env','supervisor.pid','supervisor.heartbeat','/sys/'
]:
    assert forbidden not in snapshot, 'R32 direct recurring read forbidden: '+forbidden
r.write_text(rs)

# 4) Keep R31 dynamic cloud narrative; only label this real mapping closure.
ms=m.read_text()
ms=ms.replace(
    'CONTROL CENTER • v0.12.1-r31 • DYNAMIC CLOUD REASONING',
    'CONTROL CENTER • v0.12.1-r32 • RUNTIME TRUTH MAPPING',
    1,
).replace('v0.12.1-r31','v0.12.1-r32')

# Make the learning confidence unit explicit only when it is actually numeric.
old='''@Composable fun OutcomeLearningCard(s:RuntimeState){val x=s.strategy;BoxCard("OUTCOME + LEARNING","FPS: ${x.fpsOutcome} • Frame: ${x.frameOutcome}\\nThermal: ${x.thermalOutcome} • Power: ${x.powerOutcome}\\nLearning samples: ${x.learningSamples}\\nLearning confidence: ${x.learningConfidence}\\nPromotion: ${x.learningPromotion}\\nOnly module-published truth is displayed; missing fields remain unavailable.",true)}'''
new='''@Composable fun OutcomeLearningCard(s:RuntimeState){val x=s.strategy;val lc=if(x.learningConfidence.toDoubleOrNull()!=null) "${x.learningConfidence}%" else x.learningConfidence;BoxCard("OUTCOME + LEARNING","FPS: ${x.fpsOutcome} • Frame: ${x.frameOutcome}\\nThermal: ${x.thermalOutcome} • Power: ${x.powerOutcome}\\nLearning samples: ${x.learningSamples}\\nLearning confidence: $lc\\nPromotion: ${x.learningPromotion}\\nOnly module-published truth is displayed; missing fields remain unavailable.",true)}'''
assert old in ms or new in ms, 'R32 OutcomeLearningCard anchor missing'
ms=ms.replace(old,new,1)

# Preserve R31 narrative and the existing fail-closed cards.
for required in [
    'val publishedThoughtText=thoughtField(s.thoughts,"TEXT").trim()',
    'cloudNarrativeFresh->"PEMIKIRAN $thoughtSource\\n$publishedThoughtText"',
    'BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true)',
    'BoxCard("SESSION SAFETY",(s.sessionSafety+"\\n"+s.supervisor).trim().ifBlank{"UNAVAILABLE — session safety state not published."},true)',
    'Decision source: ${x.source}',
]:
    assert required in ms, 'R32 preserved UI contract missing: '+required
m.write_text(ms)

print('R32_AUTHORITY_MAPPING=ATOMIC_CC_SNAPSHOT')
print('R32_SESSION_SAFETY_MAPPING=ATOMIC_CC_SNAPSHOT')
print('R32_SUPERVISOR_MAPPING=ATOMIC_CC_SNAPSHOT')
print('R32_DECISION_SOURCE=ATTRIBUTION_REASONER_SOURCE')
print('R32_LEARNING_SAMPLES=BRAIN_LEARNED_SAMPLES')
print('R32_LEARNING_CONFIDENCE=BRAIN_LEARNED_CONF')
print('R32_LEARNING_PROMOTION=BRAIN_LEARNING_PROMOTION')
print('R32_NO_GUESSED_VALUES=1')
print('R32_EXTRA_ROOT_POLLS=0')
print('R32_R31_DYNAMIC_REASONING=PRESERVED')
