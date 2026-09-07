#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12227',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui7"',bs,count=1)
b.write_text(bs)

ms=m.read_text()

# RT4/UI7 contract: transport truth is independent from controller selection.
# Gemini/provider state is displayed first; current brain is a separate field.
ts=ms.index('@Composable fun ThoughtsCard(s:RuntimeState)')
te=ms.index('private fun currentRange',ts)
thought=r'''@Composable fun ThoughtsCard(s:RuntimeState){
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"SOURCE")}
    val finalSource=envField(s.brain,"FINAL_SOURCE").ifBlank{envField(s.brain,"SOURCE")}
    val brainMode=envField(s.brain,"BRAIN_MODE").ifBlank{envField(s.brain,"MODE")}
    val cloudConnection=envField(s.brain,"CLOUD_CONNECTION_STATUS").ifBlank{"UNKNOWN"}
    val cloudProvider=envField(s.brain,"CLOUD_PROVIDER").ifBlank{"NONE"}
    val cloudModel=envField(s.brain,"CLOUD_MODEL").ifBlank{"—"}
    val cloudInControl=envField(s.brain,"CLOUD_IN_CONTROL").ifBlank{"NO"}
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudScore=envField(s.brain,"CLOUD_PLAN_SCORE").ifBlank{"0"}
    val cloudReason=envField(s.brain,"CLOUD_PLAN_REASON").ifBlank{"—"}
    val accountability=envField(s.brain,"CLOUD_ACCOUNTABILITY_STATUS").ifBlank{"—"}
    val thoughtSrc=envField(s.thoughts,"SOURCE")
    val thoughtFresh=envField(s.brain,"THOUGHT_FRESH")=="1"
    val thoughtAge=envField(s.brain,"THOUGHT_AGE_SEC")
    val thoughtStatus=envField(s.thoughts,"STATUS").ifBlank{"WAITING"}
    val conf=envField(s.thoughts,"CONFIDENCE")
    val text=envField(s.thoughts,"TEXT").ifBlank{"Belum ada pemikiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}
    val geminiState=if(cloudProvider=="GEMINI") cloudConnection else if(cloudConnection=="UNKNOWN") "UNKNOWN" else cloudConnection
    val thoughtLine=when{
        thoughtSrc=="GEMINI" && thoughtFresh && cloudConnection=="ONLINE" -> "PEMIKIRAN GEMINI • ONLINE"
        thoughtSrc=="GEMINI" && thoughtFresh -> "LAST GEMINI THOUGHT • CACHED • cloud=$cloudConnection"
        thoughtSrc=="GEMINI" -> "LAST GEMINI THOUGHT • STALE • age ${ageLabel(thoughtAge)}"
        thoughtSrc=="LOCAL_AI" -> "PEMIKIRAN LOCAL AI • $thoughtStatus"
        else -> "PEMIKIRAN DJAEGER • $thoughtStatus"
    }
    val memUsed=envField(s.memoryStatus,"USED_BYTES").toLongOrNull()?:0L
    val memMax=envField(s.memoryStatus,"MAX_BYTES").toLongOrNull()?:0L
    val rows=envField(s.memoryStatus,"LEDGER_ROWS").ifBlank{"0"}
    val hw=envField(s.memoryStatus,"HARDWARE_OUTCOME_ROWS").ifBlank{"0"}
    val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"
    val body="Gemini: $geminiState\nCloud provider: $cloudProvider\nCloud model: $cloudModel\nCloud in control: $cloudInControl\nCloud plan: $cloudState • $cloudScore%\nCloud reason: $cloudReason\nAccountability: $accountability\n\nActive brain: ${brainLabel(currentBrain)}\nBrain mode: ${brainMode.ifBlank{"—"}}\nFinal source: ${finalSource.ifBlank{"—"}}\n\n$thoughtLine\n$text\n\nThought source: ${thoughtSrc.ifBlank{"—"}}\nConfidence: ${conf.ifBlank{"—"}}%\n$mem"
    BoxCard("THOUGHT",body,true)
}

'''
ms=ms[:ts]+thought+ms[te:]

# Strategy mirrors the same truth: Gemini transport/policy first, then Hermes,
# selected brain, final deterministic adjustment, and Local typed validation.
ss=ms.index('@Composable fun StrategyCard(s:RuntimeState)')
se=ms.index('@Composable fun Overview(s:RuntimeState)',ss)
strategy=r'''@Composable fun StrategyCard(s:RuntimeState){
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"SOURCE")}
    val brainMode=envField(s.brain,"BRAIN_MODE").ifBlank{envField(s.brain,"MODE")}
    val brainProfile=envField(s.brain,"BRAIN_PROFILE").ifBlank{envField(s.brain,"FINAL_PROFILE")}
    val finalProfile=envField(s.brain,"FINAL_PROFILE").ifBlank{s.telemetry.profile}
    val finalSource=envField(s.brain,"FINAL_SOURCE").ifBlank{envField(s.brain,"SOURCE")}
    val adjustment=envField(s.brain,"FINAL_ADJUSTMENT").ifBlank{"NONE"}
    val execMode=envField(s.brain,"EXEC_MODE").ifBlank{"PROFILE"}
    val little=envField(s.brain,"EXEC_LITTLE")
    val big=envField(s.brain,"EXEC_BIG")
    val gpu=envField(s.brain,"EXEC_GPU")
    val cloudConnection=envField(s.brain,"CLOUD_CONNECTION_STATUS").ifBlank{"UNKNOWN"}
    val cloudProvider=envField(s.brain,"CLOUD_PROVIDER").ifBlank{"NONE"}
    val cloudModel=envField(s.brain,"CLOUD_MODEL").ifBlank{"—"}
    val cloudControl=envField(s.brain,"CLOUD_IN_CONTROL").ifBlank{"NO"}
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudScore=envField(s.brain,"CLOUD_PLAN_SCORE").ifBlank{"0"}
    val cloudReason=envField(s.brain,"CLOUD_PLAN_REASON").ifBlank{"—"}
    val accountability=envField(s.brain,"CLOUD_ACCOUNTABILITY_STATUS").ifBlank{"—"}
    val hermesState=envField(s.brain,"HERMES_PROPOSAL_STATE").ifBlank{envField(s.brain,"HERMES_STATE").ifBlank{"—"}}
    val hermesConf=envField(s.brain,"HERMES_PROPOSAL_CONFIDENCE").ifBlank{envField(s.brain,"HERMES_CONFIDENCE").ifBlank{"0"}}
    val srValidation=envField(s.strategyResult,"VALIDATION")
    val srReadback=envField(s.strategyResult,"READBACK")
    val srOutcome=envField(s.strategyResult,"OUTCOME")
    val validation=if(srValidation.isNotBlank()) "$srValidation • readback=${srReadback.ifBlank{"—"}} • outcome=${srOutcome.ifBlank{"—"}}" else "LOCAL VALIDATOR / FAIL-CLOSED"
    val body="Gemini: $cloudConnection • provider=$cloudProvider • model=$cloudModel\nGemini in control: $cloudControl\nGemini plan: $cloudState • $cloudScore%\nGemini reason: $cloudReason\nAccountability: $accountability\nHermes proposal: $hermesState • ${hermesConf}%\nCurrent brain: ${brainLabel(currentBrain)}\nBrain decision: ${brainMode.ifBlank{"—"}}\nBrain profile: ${brainProfile.ifBlank{"—"}}\nFinal profile / mode: $finalProfile / $execMode\nFinal source: ${finalSource.ifBlank{"—"}}\nFinal adjustment: $adjustment\nUser mode: ${s.userMode}\nCPU little: ${currentRange(little,"kHz")}\nCPU big: ${currentRange(big,"kHz")}\nGPU: ${currentRange(gpu,"MHz")}\nValidasi Local AI: $validation"
    BoxCard("STRATEGI",body,true)
}

'''
ms=ms[:ss]+strategy+ms[se:]

old='CONTROL CENTER • v0.12.1-r22-r92ui6 • HERMES H2 RT3 SYNC'
new='CONTROL CENTER • v0.12.1-r22-r92ui7 • GEMINI FIRST RT4 SYNC'
assert old in ms, 'RT4_UI7_FAIL=header-anchor'
ms=ms.replace(old,new,1)

# Approved layout stays exact. Cloud-active inference is forbidden in UI7.
assert 'StatusCard(s);ThoughtsCard(s);HermesCard(s);StrategyCard(s);OutcomeLearningCard(s);' in ms
for required in ['CLOUD_CONNECTION_STATUS','CLOUD_PROVIDER','CLOUD_MODEL','CLOUD_IN_CONTROL','CLOUD_PLAN_STATE','CLOUD_PLAN_REASON','CLOUD_ACCOUNTABILITY_STATUS','CURRENT_BRAIN','HERMES_PROPOSAL_STATE','THOUGHT_FRESH']:
    assert required in ms, required
assert 'Cloud active:' not in ms
assert 'if(currentBrain=="GEMINI") "GEMINI" else "NONE"' not in ms
for forbidden in ['/sys/','iptables','ip6tables','settings put','setprop','force-stop','ProcessBuilder']:
    assert forbidden not in thought+strategy, forbidden
m.write_text(ms)

print('RT4_UI7_BASELINE=R92_UI6_SOURCE_NATIVE')
print('RT4_UI7_ORDER=THOUGHT>HERMES>STRATEGI>OUTCOME')
print('RT4_UI7_GEMINI_FIRST=YES')
print('RT4_UI7_CLOUD_TRUTH=TRANSPORT_SEPARATE_FROM_BRAIN')
print('RT4_UI7_CLOUD_ACTIVE_NONE=REMOVED')
print('RT4_UI7_AUTHORITY_CHANGE=NONE')
