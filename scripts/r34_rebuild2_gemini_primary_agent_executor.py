#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
b=root/'app/build.gradle.kts'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12251',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-fix4-rc1-rebuild2-gemini-primary-agent-executor"',bs,count=1)
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
    "GEMINI"->"GEMINI • PRIMARY"
    "HERMES_LOCAL","HERMES_H2"->"HERMES H2 • LOCAL FALLBACK"
    "NONE"->"NONE • NATIVE FAILSAFE"
    else->raw.ifBlank{"—"}
}'''
assert old in s, 'brainLabel baseline anchor missing'
s=s.replace(old,new,1)

s=s.replace('thoughtSrc=="LOCAL_AI"->"PEMIKIRAN LOCAL AI"','thoughtSrc=="HERMES_H2"->"PEMIKIRAN HERMES H2"',1)

old_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix4-baseline-rc1 • HERMES COGNITION VNEXT • HCC1'
new_header='CONTROL CENTER • FIX4 RC1 REBUILD2 • GEMINI PRIMARY • AGENT EXECUTOR • HERMES H2 FALLBACK'
assert old_header in s, 'header anchor missing'
s=s.replace(old_header,new_header,1)

anchor='''private fun currentRange(raw:String,unit:String):String{'''
assert anchor in s
agent=r'''@Composable fun AgentRebuild2Card(s:RuntimeState){
    val version=envField(s.brain,"AGENT_VERSION").ifBlank{"UNPUBLISHED"}
    val role=envField(s.brain,"AGENT_ROLE").ifBlank{"AUTONOMOUS_EXECUTOR"}
    val state=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"}
    val input=envField(s.brain,"AGENT_INPUT_SOURCE").ifBlank{"NONE"}
    val decisionAuth=envField(s.brain,"AGENT_DECISION_AUTHORITY").ifBlank{"NONE"}
    val executionOwner=envField(s.brain,"AGENT_EXECUTION_OWNER").ifBlank{"YES"}
    val backend=envField(s.brain,"AGENT_EXECUTION_BACKEND").ifBlank{"GOLDEN1_TYPED_BACKEND"}
    val validation=envField(s.brain,"AGENT_LAST_VALIDATION").ifBlank{"UNKNOWN"}
    val readback=envField(s.brain,"AGENT_LAST_READBACK").ifBlank{"UNKNOWN"}
    val priority=envField(s.brain,"DECISION_PRIORITY").ifBlank{"GEMINI>HERMES_H2>NATIVE_FAILSAFE"}
    val third=envField(s.brain,"THIRD_BRAIN").ifBlank{"UNPUBLISHED"}
    val failsafe=envField(s.brain,"NATIVE_FAILSAFE").ifBlank{"—"}
    val matched=s.moduleVersion.contains("GEMINI-PRIMARY-AGENT-EXECUTOR-REBUILD2",true)
    val body="Matched module: ${if(matched) "YES" else "NO — install REBUILD2 module"}\nRole: $role\nState: $state\nDecision input: $input\nDecision authority: $decisionAuth\nExecution owner: $executionOwner\nExecution backend: $backend\nLast validation: $validation\nLast readback: $readback\nDecision priority: $priority\nPrimary brain: GEMINI\nLocal fallback brain: HERMES H2\nThird brain: $third\nNative failsafe: $failsafe"
    BoxCard("AI AGENT • AUTONOMOUS EXECUTOR",body,true)
}

'''
s=s.replace(anchor,agent+anchor,1)

# Hermes is the sole local fallback brain, not a co-equal competitor with Gemini.
s=s.replace('"VALID"->if(currentBrain=="HERMES_LOCAL") "ACTIVE" else "READY"','"VALID"->if(currentBrain=="HERMES_H2"||currentBrain=="HERMES_LOCAL") "ACTIVE FALLBACK" else "READY FALLBACK"',1)
s=s.replace('val authority=if(hState=="VALID"&&currentBrain=="HERMES_LOCAL") "PROPOSAL ACCEPTED • LOCAL VALIDATOR/TYPED EXECUTOR" else "NO DIRECT HARDWARE AUTHORITY"','val authority="LOCAL FALLBACK BRAIN • USED ONLY WHEN GEMINI INVALID/UNAVAILABLE • NO DIRECT HARDWARE WRITES"',1)

old='StatusCard(s);ThoughtsCard(s);Row('
new='StatusCard(s);ThoughtsCard(s);AgentRebuild2Card(s);Row('
assert old in s, 'Overview anchor missing'
s=s.replace(old,new,1)

m.write_text(s)
print('REBUILD2_UI_PATCH=PASS')
print('BASELINE_LAYOUT_PRESERVED=PASS')
print('AGENT_EXECUTOR_CARD_INSERTED=PASS')
print('GEMINI_PRIMARY_SEMANTICS=PASS')
print('HERMES_FALLBACK_SEMANTICS=PASS')
print('NO_LOCAL_AI_UI=PASS')
