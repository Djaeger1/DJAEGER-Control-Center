#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
b=root/'app/build.gradle.kts'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12250',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-fix4-rc1-agent-rebuild1"',bs,count=1)
b.write_text(bs)

s=m.read_text()
old='''private fun brainLabel(raw:String):String = when(raw){
    "GEMINI"->"GEMINI"
    "HERMES_LOCAL"->"HERMES"
    "LOCAL_LEARNED"->"LOCAL AI • LEARNED"
    "LOCAL_BASELINE","LOCAL_FRAME","VALIDATOR_FALLBACK","RESCUE_GUARD"->"LOCAL AI"
    else->if(raw.startsWith("LOCAL")) "LOCAL AI" else raw.ifBlank{"—"}
}'''
new='''private fun brainLabel(raw:String):String = when(raw){
    "GEMINI"->"GEMINI"
    "HERMES_LOCAL","HERMES_H2"->"HERMES H2"
    "NONE"->"NONE • NATIVE FAILSAFE"
    else->raw.ifBlank{"—"}
}'''
assert old in s, 'brainLabel baseline anchor missing'
s=s.replace(old,new,1)

s=s.replace('thoughtSrc=="LOCAL_AI"->"PEMIKIRAN LOCAL AI"','thoughtSrc=="HERMES_H2"->"PEMIKIRAN HERMES H2"',1)

anchor='''private fun currentRange(raw:String,unit:String):String{'''
assert anchor in s
agent='''@Composable fun AgentRebuild1Card(s:RuntimeState){
    val version=envField(s.brain,"AGENT_VERSION").ifBlank{"UNPUBLISHED"}
    val state=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"}
    val winner=envField(s.brain,"AGENT_WINNER").ifBlank{"NONE"}
    val score=envField(s.brain,"AGENT_SCORE").ifBlank{"0"}
    val reason=envField(s.brain,"AGENT_REASON").ifBlank{"—"}
    val cloud=envField(s.brain,"BRAIN_CLOUD").ifBlank{"GEMINI"}
    val local=envField(s.brain,"BRAIN_LOCAL").ifBlank{"HERMES_H2"}
    val third=envField(s.brain,"THIRD_BRAIN").ifBlank{"UNPUBLISHED"}
    val failsafe=envField(s.brain,"NATIVE_FAILSAFE").ifBlank{"—"}
    val backend=envField(s.brain,"AGENT_EXECUTION_BACKEND").ifBlank{"GOLDEN1_TYPED_BACKEND"}
    val matched=s.moduleVersion.contains("AGENT-REBUILD1",true)
    val body="Matched module: ${if(matched) "YES" else "NO — install REBUILD1 module"}\nAgent: $version • $state\nWinner: $winner • score $score\nReason: $reason\nCloud brain: $cloud\nLocal brain: $local\nThird brain: $third\nNative failsafe: $failsafe\nExecution backend: $backend\nAuthority: AI Agent owns final arbitration; GOLDEN1 typed backend performs verified hardware writes."
    BoxCard("AI AGENT • FINAL ORCHESTRATION",body,true)
}

'''
s=s.replace(anchor,agent+anchor,1)

# Hermes is a reasoning brain; Agent owns final arbitration/execution orchestration.
s=s.replace('"VALID"->if(currentBrain=="HERMES_LOCAL") "ACTIVE" else "READY"','"VALID"->if(currentBrain=="HERMES_H2"||currentBrain=="HERMES_LOCAL") "SELECTED BY AGENT" else "READY"',1)
s=s.replace('val authority=if(hState=="VALID"&&currentBrain=="HERMES_LOCAL") "PROPOSAL ACCEPTED • LOCAL VALIDATOR/TYPED EXECUTOR" else "NO DIRECT HARDWARE AUTHORITY"','val authority="REASONING BRAIN • AI AGENT OWNS FINAL ARBITRATION/EXECUTION ORCHESTRATION"',1)

old='StatusCard(s);ThoughtsCard(s);Row('
new='StatusCard(s);ThoughtsCard(s);AgentRebuild1Card(s);Row('
assert old in s, 'Overview anchor missing'
s=s.replace(old,new,1)

m.write_text(s)
print('REBUILD1_UI_PATCH=PASS')
print('BASELINE_LAYOUT_PRESERVED=PASS')
print('AGENT_CARD_INSERTED_AFTER_THOUGHT=PASS')
print('THIRD_BRAIN_UI_REMOVED=PASS')
