#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12228',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix1"',bs,count=1)
b.write_text(bs)

ms=m.read_text()

# Preserve UI6 layout/cards. Fix only the semantics shown inside THOUGHT/STRATEGI.
ts=ms.index('@Composable fun ThoughtsCard(s:RuntimeState)')
te=ms.index('private fun currentRange',ts)
thought=r'''@Composable fun ThoughtsCard(s:RuntimeState){
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"SOURCE")}
    val finalSource=envField(s.brain,"FINAL_SOURCE").ifBlank{envField(s.brain,"SOURCE")}
    val brainMode=envField(s.brain,"BRAIN_MODE").ifBlank{envField(s.brain,"MODE")}
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudConnection=envField(s.brain,"CLOUD_CONNECTION_STATUS").ifBlank{"UNKNOWN"}
    val cloudProvider=envField(s.brain,"CLOUD_PROVIDER").ifBlank{if(cloudConnection!="UNKNOWN") "GEMINI" else "—"}
    val cloudInControl=envField(s.brain,"CLOUD_IN_CONTROL").ifBlank{if(currentBrain=="GEMINI") "YES" else "NO"}
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
    val statusLabel=when{
        thoughtSrc=="GEMINI"&&!isFresh->"STALE • age ${ageLabel(thoughtAge)}"
        thoughtSrc=="GEMINI"->cloudConnection
        else->thoughtStatus
    }
    val geminiLine=if(cloudProvider=="GEMINI") "GEMINI • $cloudConnection" else cloudConnection
    val memUsed=envField(s.memoryStatus,"USED_BYTES").toLongOrNull()?:0L
    val memMax=envField(s.memoryStatus,"MAX_BYTES").toLongOrNull()?:0L
    val rows=envField(s.memoryStatus,"LEDGER_ROWS").ifBlank{"0"}
    val hw=envField(s.memoryStatus,"HARDWARE_OUTCOME_ROWS").ifBlank{"0"}
    val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"
    val body="Gemini: $geminiLine\nActive brain: ${brainLabel(currentBrain)}\nCloud in control: $cloudInControl\nBrain mode: ${brainMode.ifBlank{"—"}}\nFinal source: ${finalSource.ifBlank{"—"}}\nCloud plan: $cloudState\n\n$thoughtTitle • $statusLabel\n$text\n\nThought source: ${thoughtSrc.ifBlank{"—"}}\nConfidence: ${conf.ifBlank{"—"}}%\n$mem"
    BoxCard("THOUGHT",body,true)
}

'''
ms=ms[:ts]+thought+ms[te:]

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
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudScore=envField(s.brain,"CLOUD_PLAN_SCORE").ifBlank{"0"}
    val cloudReason=envField(s.brain,"CLOUD_PLAN_REASON").ifBlank{"—"}
    val hermesState=envField(s.brain,"HERMES_PROPOSAL_STATE").ifBlank{envField(s.brain,"HERMES_STATE").ifBlank{"—"}}
    val hermesConf=envField(s.brain,"HERMES_PROPOSAL_CONFIDENCE").ifBlank{envField(s.brain,"HERMES_CONFIDENCE").ifBlank{"0"}}
    val srValidation=envField(s.strategyResult,"VALIDATION")
    val srReadback=envField(s.strategyResult,"READBACK")
    val srOutcome=envField(s.strategyResult,"OUTCOME")
    val validation=if(srValidation.isNotBlank()) "$srValidation • readback=${srReadback.ifBlank{"—"}} • outcome=${srOutcome.ifBlank{"—"}}" else "LOCAL VALIDATOR / FAIL-CLOSED"
    val body="Gemini: $cloudConnection\nTruth: CURRENT BRAIN / FUSED\nCloud proposal: $cloudState • ${cloudScore}%\nCloud reason: $cloudReason\nHermes proposal: $hermesState • ${hermesConf}%\nCurrent brain: ${brainLabel(currentBrain)}\nBrain decision: ${brainMode.ifBlank{"—"}}\nBrain profile: ${brainProfile.ifBlank{"—"}}\nFinal profile / mode: $finalProfile / $execMode\nFinal source: ${finalSource.ifBlank{"—"}}\nFinal adjustment: $adjustment\nUser mode: ${s.userMode}\nCPU little: ${currentRange(little,"kHz")}\nCPU big: ${currentRange(big,"kHz")}\nGPU: ${currentRange(gpu,"MHz")}\nValidasi Local AI: $validation"
    BoxCard("STRATEGI",body,true)
}

'''
ms=ms[:ss]+strategy+ms[se:]

old='CONTROL CENTER • v0.12.1-r22-r92ui6 • HERMES H2 RT3 SYNC'
new='CONTROL CENTER • v0.12.1-r22-r92ui6-fix1 • HERMES H2 RT3 FIX1'
assert old in ms, 'UI6_FIX1_FAIL=header-anchor'
ms=ms.replace(old,new,1)

# UI6 presentation contract stays intact.
assert 'StatusCard(s);ThoughtsCard(s);HermesCard(s);StrategyCard(s);OutcomeLearningCard(s);' in ms
assert ms.count('OutcomeLearningCard(s);')==1
assert 'HERMES H2 • LOCAL BRAIN' in ms
assert 'BoxCard("THOUGHT",body,true)' in ms
assert 'BoxCard("STRATEGI",body,true)' in ms
assert 'Cloud active:' not in ms
assert 'if(currentBrain=="GEMINI") "GEMINI" else "NONE"' not in ms
thought_block=ms[ms.index('@Composable fun ThoughtsCard'):ms.index('private fun currentRange',ms.index('@Composable fun ThoughtsCard'))]
assert thought_block.index('Gemini: $geminiLine') < thought_block.index('Active brain:')
for required in ['CLOUD_CONNECTION_STATUS','CLOUD_PROVIDER','CLOUD_IN_CONTROL','CLOUD_PLAN_STATE','CURRENT_BRAIN','FINAL_SOURCE','THOUGHT_FRESH']:
    assert required in ms, required
for forbidden in ['/sys/','iptables','ip6tables','settings put','setprop','force-stop','ProcessBuilder']:
    assert forbidden not in thought+strategy, forbidden
m.write_text(ms)

print('UI6_FIX1_BASELINE=UI6_RT3_COMMIT_52ee656')
print('UI6_FIX1_LAYOUT=UI6_PRESERVED')
print('UI6_FIX1_GEMINI_FIRST_DISPLAY=PASS')
print('UI6_FIX1_CLOUD_TRANSPORT_SEPARATE_FROM_BRAIN=PASS')
print('UI6_FIX1_CLOUD_ACTIVE_NONE_REMOVED=PASS')
print('UI6_FIX1_AUTHORITY_CHANGE=NONE')
