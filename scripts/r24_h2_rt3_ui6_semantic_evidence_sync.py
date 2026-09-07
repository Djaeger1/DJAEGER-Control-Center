#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12226',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6"',bs,count=1)
b.write_text(bs)

ms=m.read_text()

# Replace UI2/5 semantic helpers + Thought card. Module RT3 publishes explicit
# CURRENT_BRAIN/FINAL_SOURCE and thought freshness in the same atomic brain block.
start=ms.index('private fun effectiveSourceLabel')
end=ms.index('private fun currentRange',start)
thought=r'''private fun brainLabel(raw:String):String = when(raw){
    "GEMINI"->"GEMINI"
    "HERMES_LOCAL"->"HERMES"
    "LOCAL_LEARNED"->"LOCAL AI • LEARNED"
    "LOCAL_BASELINE","LOCAL_FRAME","VALIDATOR_FALLBACK","RESCUE_GUARD"->"LOCAL AI"
    else->if(raw.startsWith("LOCAL")) "LOCAL AI" else raw.ifBlank{"—"}
}
private fun ageLabel(raw:String):String{
    val n=raw.toLongOrNull()?:return "—"
    if(n<0)return "—"
    return when{n<60->"${n}s";n<3600->"${n/60}m ${n%60}s";else->"${n/3600}h ${(n%3600)/60}m"}
}

@Composable fun ThoughtsCard(s:RuntimeState){
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"SOURCE")}
    val finalSource=envField(s.brain,"FINAL_SOURCE").ifBlank{envField(s.brain,"SOURCE")}
    val brainMode=envField(s.brain,"BRAIN_MODE").ifBlank{envField(s.brain,"MODE")}
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE")
    val thoughtSrc=envField(s.thoughts,"SOURCE")
    val thoughtStatus=envField(s.thoughts,"STATUS").ifBlank{"WAITING"}
    val thoughtFresh=envField(s.brain,"THOUGHT_FRESH")
    val thoughtAge=envField(s.brain,"THOUGHT_AGE_SEC")
    val conf=envField(s.thoughts,"CONFIDENCE")
    val text=envField(s.thoughts,"TEXT").ifBlank{"Belum ada pemikiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}
    val isFresh=thoughtFresh=="1"
    val thoughtTitle=when{
        thoughtSrc=="GEMINI"&&isFresh->"PEMIKIRAN GEMINI"
        thoughtSrc=="GEMINI"->"LAST GEMINI THOUGHT"
        thoughtSrc=="LOCAL_AI"->"PEMIKIRAN LOCAL AI"
        else->"PEMIKIRAN DJAEGER"
    }
    val statusLabel=if(thoughtSrc=="GEMINI"&&!isFresh) "STALE • age ${ageLabel(thoughtAge)}" else thoughtStatus
    val cloudActive=if(currentBrain=="GEMINI") "GEMINI" else "NONE"
    val memUsed=envField(s.memoryStatus,"USED_BYTES").toLongOrNull()?:0L
    val memMax=envField(s.memoryStatus,"MAX_BYTES").toLongOrNull()?:0L
    val rows=envField(s.memoryStatus,"LEDGER_ROWS").ifBlank{"0"}
    val hw=envField(s.memoryStatus,"HARDWARE_OUTCOME_ROWS").ifBlank{"0"}
    val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"
    val body="Active brain: ${brainLabel(currentBrain)}\nCloud active: $cloudActive\nBrain mode: ${brainMode.ifBlank{"—"}}\nFinal source: ${finalSource.ifBlank{"—"}}\nCloud plan: ${cloudState.ifBlank{"—"}}\n\n$thoughtTitle • $statusLabel\n$text\n\nThought source: ${thoughtSrc.ifBlank{"—"}}\nConfidence: ${conf.ifBlank{"—"}}%\n$mem"
    BoxCard("THOUGHT",body,true)
}

'''
ms=ms[:start]+thought+ms[end:]

# Dedicated Hermes card: proposal truth and context-scoped evidence are separate
# from final execution attribution.
hs=ms.index('@Composable fun HermesCard(s:RuntimeState)')
he=ms.index('@Composable fun StrategyCard(s:RuntimeState)',hs)
hermes=r'''@Composable fun HermesCard(s:RuntimeState){
    val hState=envField(s.brain,"HERMES_PROPOSAL_STATE").ifBlank{envField(s.brain,"HERMES_STATE").ifBlank{"UNAVAILABLE"}}
    val hProfile=envField(s.brain,"HERMES_PROFILE").ifBlank{"—"}
    val hConfidence=envField(s.brain,"HERMES_PROPOSAL_CONFIDENCE").ifBlank{envField(s.brain,"HERMES_CONFIDENCE").ifBlank{"0"}}
    val hMode=envField(s.brain,"HERMES_MODE").ifBlank{"PROFILE"}
    val hVariable=envField(s.brain,"HERMES_VARIABLE").ifBlank{"NA"}
    val hValue=envField(s.brain,"HERMES_VARIABLE_VALUE").ifBlank{"0"}
    val hVariableState=envField(s.brain,"HERMES_VARIABLE_STATE").ifBlank{"NONE"}
    val hSamples=envField(s.brain,"HERMES_VARIABLE_SAMPLES").ifBlank{"0"}
    val hRate=envField(s.brain,"HERMES_VARIABLE_SUCCESS_RATE").ifBlank{"0"}
    val hScope=envField(s.brain,"HERMES_EVIDENCE_SCOPE").ifBlank{"—"}
    val hFilter=envField(s.brain,"HERMES_EVIDENCE_FILTER").ifBlank{"—"}
    val hReason=envField(s.brain,"HERMES_REASON").ifBlank{"Belum ada reasoning Hermes yang dipublikasikan module."}
    val currentBrain=envField(s.brain,"CURRENT_BRAIN")
    val finalSource=envField(s.brain,"FINAL_SOURCE")
    val displayState=when(hState){
        "VALID"->if(currentBrain=="HERMES_LOCAL") "ACTIVE" else "READY"
        "STANDBY_GEMINI_ONLINE"->"STANDBY • GEMINI VALID"
        "LOW_CONFIDENCE"->"LEARNING • LOW CONFIDENCE"
        "UNAVAILABLE"->"UNAVAILABLE"
        else->hState
    }
    val authority=if(hState=="VALID"&&currentBrain=="HERMES_LOCAL") "PROPOSAL ACCEPTED • LOCAL VALIDATOR/TYPED EXECUTOR" else "NO DIRECT HARDWARE AUTHORITY"
    val body="State: $displayState\nMode: $hMode\nProfile: $hProfile\nConfidence: $hConfidence%\nVariable: $hVariable\nValue: $hValue\nVariable state: $hVariableState\nContext samples: $hSamples\nContext success rate: $hRate%\nEvidence scope: $hScope\nEvidence filter: $hFilter\nBrain source: ${currentBrain.ifBlank{"—"}}\nFinal source: ${finalSource.ifBlank{"—"}}\nAuthority: $authority\nReason: $hReason"
    BoxCard("HERMES H2 • LOCAL BRAIN",body,true)
}

'''
ms=ms[:hs]+hermes+ms[he:]

# Strategy explicitly separates Cloud proposal, Hermes proposal, chosen brain,
# and any deterministic post-decision adjustment.
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
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{envField(s.brain,"SHADOW_STATE").ifBlank{"—"}}
    val cloudScore=envField(s.brain,"CLOUD_PLAN_SCORE").ifBlank{envField(s.brain,"SHADOW_SCORE").ifBlank{"—"}}
    val cloudReason=envField(s.brain,"CLOUD_PLAN_REASON").ifBlank{envField(s.brain,"SHADOW_REASON").ifBlank{"—"}}
    val hermesState=envField(s.brain,"HERMES_PROPOSAL_STATE").ifBlank{envField(s.brain,"HERMES_STATE").ifBlank{"—"}}
    val hermesConf=envField(s.brain,"HERMES_PROPOSAL_CONFIDENCE").ifBlank{envField(s.brain,"HERMES_CONFIDENCE").ifBlank{"0"}}
    val srValidation=envField(s.strategyResult,"VALIDATION")
    val srReadback=envField(s.strategyResult,"READBACK")
    val srOutcome=envField(s.strategyResult,"OUTCOME")
    val validation=if(srValidation.isNotBlank()) "$srValidation • readback=${srReadback.ifBlank{"—"}} • outcome=${srOutcome.ifBlank{"—"}}" else "LOCAL VALIDATOR / FAIL-CLOSED"
    val body="Truth: CURRENT BRAIN / FUSED\nCloud proposal: $cloudState • ${cloudScore}%\nCloud reason: $cloudReason\nHermes proposal: $hermesState • ${hermesConf}%\nCurrent brain: ${brainLabel(currentBrain)}\nBrain decision: ${brainMode.ifBlank{"—"}}\nBrain profile: ${brainProfile.ifBlank{"—"}}\nFinal profile / mode: $finalProfile / $execMode\nFinal source: ${finalSource.ifBlank{"—"}}\nFinal adjustment: $adjustment\nUser mode: ${s.userMode}\nCPU little: ${currentRange(little,"kHz")}\nCPU big: ${currentRange(big,"kHz")}\nGPU: ${currentRange(gpu,"MHz")}\nValidasi Local AI: $validation"
    BoxCard("STRATEGI",body,true)
}

'''
ms=ms[:ss]+strategy+ms[se:]

old='CONTROL CENTER • v0.12.1-r22-r92ui5 • HERMES H2 RT2 SYNC'
new='CONTROL CENTER • v0.12.1-r22-r92ui6 • HERMES H2 RT3 SYNC'
assert old in ms, 'H2_UI6_FAIL=header-anchor'
ms=ms.replace(old,new,1)

# Exact approved layout remains unchanged.
assert 'StatusCard(s);ThoughtsCard(s);HermesCard(s);StrategyCard(s);OutcomeLearningCard(s);' in ms
for required in ['CURRENT_BRAIN','FINAL_SOURCE','FINAL_ADJUSTMENT','CLOUD_PLAN_STATE','HERMES_PROPOSAL_STATE','HERMES_EVIDENCE_SCOPE','THOUGHT_FRESH','LAST GEMINI THOUGHT']:
    assert required in ms, required
for forbidden in ['/sys/','iptables','ip6tables','settings put','setprop','force-stop','ProcessBuilder']:
    assert forbidden not in thought+hermes+strategy, forbidden
m.write_text(ms)

print('H2_UI6_BASELINE=R92_UI5_SOURCE_NATIVE')
print('H2_UI6_ORDER=THOUGHT>HERMES>STRATEGI>OUTCOME')
print('H2_UI6_SEMANTICS=BRAIN_PROPOSAL_FINAL_SPLIT')
print('H2_UI6_THOUGHT_FRESHNESS=MODULE_PUBLISHED')
print('H2_UI6_HERMES_EVIDENCE=CONTEXT_SCOPED')
print('H2_UI6_AUTHORITY_CHANGE=NONE')
