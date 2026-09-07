#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12225',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui5"',bs,count=1)
b.write_text(bs)

ms=m.read_text()

# Dedicated Hermes card. It is presentation-only and reads module-published
# HERMES_* fields from the same fused brain snapshot already trusted by UI2.
anchor='@Composable fun StrategyCard(s:RuntimeState)'
assert anchor in ms, 'H2_UI5_FAIL=strategy-card-anchor'
hermes=r'''@Composable fun HermesCard(s:RuntimeState){
    val hState=envField(s.brain,"HERMES_STATE").ifBlank{"UNAVAILABLE"}
    val hProfile=envField(s.brain,"HERMES_PROFILE").ifBlank{"—"}
    val hConfidence=envField(s.brain,"HERMES_CONFIDENCE").ifBlank{"0"}
    val hMode=envField(s.brain,"HERMES_MODE").ifBlank{"PROFILE"}
    val hVariable=envField(s.brain,"HERMES_VARIABLE").ifBlank{"NA"}
    val hValue=envField(s.brain,"HERMES_VARIABLE_VALUE").ifBlank{"0"}
    val hVariableState=envField(s.brain,"HERMES_VARIABLE_STATE").ifBlank{"NONE"}
    val hSamples=envField(s.brain,"HERMES_VARIABLE_SAMPLES").ifBlank{"0"}
    val hRate=envField(s.brain,"HERMES_VARIABLE_SUCCESS_RATE").ifBlank{"0"}
    val hReason=envField(s.brain,"HERMES_REASON").ifBlank{"Belum ada reasoning Hermes yang dipublikasikan module."}
    val hSource=envField(s.brain,"SOURCE").ifBlank{"—"}
    val displayState=when(hState){
        "VALID"->"ACTIVE"
        "STANDBY_GEMINI_ONLINE"->"STANDBY • GEMINI VALID"
        "LOW_CONFIDENCE"->"LEARNING • LOW CONFIDENCE"
        "UNAVAILABLE"->"UNAVAILABLE"
        else->hState
    }
    val authority=if(hState=="VALID"&&hSource=="HERMES_LOCAL") "PROPOSAL ACCEPTED • TYPED EXECUTOR" else "NO DIRECT HARDWARE AUTHORITY"
    val body="State: $displayState\nMode: $hMode\nProfile: $hProfile\nConfidence: $hConfidence%\nVariable: $hVariable\nValue: $hValue\nVariable state: $hVariableState\nSamples: $hSamples\nSuccess rate: $hRate%\nEffective source: $hSource\nAuthority: $authority\nReason: $hReason"
    BoxCard("HERMES H2 • LOCAL BRAIN",body,true)
}

'''
ms=ms.replace(anchor,hermes+anchor,1)

# Exact Overview information flow requested by the user:
# THOUGHT -> HERMES H2 -> STRATEGI -> OUTCOME + LEARNING.
# Outcome remains its original module-published card; it is only moved.
assert ms.count('OutcomeLearningCard(s);')==1, 'H2_UI5_FAIL=outcome-call-count'
ms=ms.replace('OutcomeLearningCard(s);','',1)
order='StatusCard(s);ThoughtsCard(s);StrategyCard(s);'
assert order in ms, 'H2_UI5_FAIL=overview-order-anchor'
ms=ms.replace(order,'StatusCard(s);ThoughtsCard(s);HermesCard(s);StrategyCard(s);OutcomeLearningCard(s);',1)

# Match the approved mockup naming while preserving the existing Thoughts body.
ms=ms.replace('BoxCard("THOUGHTS",body,true)','BoxCard("THOUGHT",body,true)',1)

old_header='CONTROL CENTER • v0.12.1-r22-r92ui2 • R92 MODULE-SYNC TRUTH'
new_header='CONTROL CENTER • v0.12.1-r22-r92ui5 • HERMES H2 RT2 SYNC'
assert old_header in ms, 'H2_UI5_FAIL=header-anchor'
ms=ms.replace(old_header,new_header,1)

# Safety / scope assertions: UI remains observer-only.
for forbidden in ['/sys/','iptables','ip6tables','settings put','setprop','force-stop']:
    assert forbidden not in hermes, forbidden
assert 'ProcessBuilder' not in hermes
assert 'HermesCard(s);StrategyCard(s);OutcomeLearningCard(s);' in ms
assert 'HERMES_VARIABLE_SUCCESS_RATE' in ms
assert 'HERMES H2 • LOCAL BRAIN' in ms
m.write_text(ms)

print('H2_UI5_BASELINE=R92_UI2_SOURCE')
print('H2_UI5_OVERVIEW_ORDER=THOUGHT>HERMES>STRATEGI>OUTCOME')
print('H2_UI5_HERMES_SOURCE=BRAIN_HERMES_FIELDS')
print('H2_UI5_HARDWARE_AUTHORITY=NONE')
print('H2_UI5_NETWORK_CHANGE=NONE')
